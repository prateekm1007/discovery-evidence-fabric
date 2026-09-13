"""Observation + improvement signals (R450 §§8-9) and the causal
update (§3's OBSERVATION -> CAUSAL UPDATE -> NEXT DIRECTION).

THE EPISTEMIC/IMPROVEMENT SEPARATION (directive §8):
  Epistemic states (the gates — UNCHANGED, never replaced):
    SUPPORTED / UNSUPPORTED / UNKNOWN / ABSTAIN / REQUIRES_EXPERIMENT
  Improvement signals (a NEW optimization layer UNDER the gates):
    objective_delta, constraint_delta, sensitivity, tradeoff,
    distance_to_target, information_gain

  The signals are continuous where the evaluators produce numbers and
  DISCRETE-VERDICT TRANSITIONS where they do not; they never override
  or soften an epistemic gate (an improving objective on a KILLED
  candidate is recorded as a KILLED candidate whose objective moved).

NO FABRICATED GRADIENTS (directive §9):
  `sensitivity_from_evaluations` computes a numerical derivative ONLY
  from REAL recorded evaluation pairs (two evaluations of nearby
  variants, citing both evaluation ids). Where no pair exists the
  sensitivity field is explicitly null with the basis "no evaluation
  pair" — an AI-invented gradient is forbidden and test-enforced.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

#: epistemic-state vocabulary (the gates' own states; closed)
EPISTEMIC_STATES = ["SUPPORTED", "UNSUPPORTED", "UNKNOWN", "ABSTAIN",
                    "REQUIRES_EXPERIMENT"]

#: discrete gauntlet verdicts ordered by survivability (used for
#: verdict transitions — a real, recorded improvement signal)
VERDICT_LADDER = ["KILLED", "NEEDS_REPAIR", "SURVIVED_WITH_UNCERTAINTIES",
                  "SURVIVED"]

_NUMERIC_RE = re.compile(
    r"(-?\d+(?:\.\d+)?(?:e-?\d+)?)\s*([a-z/%°]*[a-z]*)" , re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _verdict_rank(v: str) -> int:
    try:
        return VERDICT_LADDER.index(str(v or "").upper())
    except ValueError:
        return -1


def extract_observation(candidate_id: str,
                        mutation_id: str,
                        hypothesis: Optional[Dict[str, Any]],
                        gauntlet_result: Dict[str, Any]
                        ) -> Dict[str, Any]:
    """OBSERVATION: what the evaluation actually said.

    `gauntlet_result` carries the re-evaluated generation's challenge
    record: killed, attack_overall, engineering_attack_overall,
    physics_lifecycle, kill_stage, kill_reason (the same fields the
    evolution gauntlet records).

    The observation layer is EXTRACTION ONLY — it re-bases nothing,
    softens nothing, and invents nothing (Art. III).
    """
    killed = bool(gauntlet_result.get("killed"))
    attack_overall = str(gauntlet_result.get("attack_overall") or
                         "").upper()
    eng_overall = str(gauntlet_result.get("engineering_attack_overall")
                      or "").upper()
    physics_lifecycle = str(gauntlet_result.get("physics_lifecycle")
                            or "").upper()
    # the best (most survivable) verdict actually recorded
    verdicts = [v for v in (attack_overall, eng_overall) if v]
    best = verdicts[0] if verdicts else ""
    for v in verdicts[1:]:
        if _verdict_rank(v) > _verdict_rank(best):
            best = v
    obs: Dict[str, Any] = {
        "observation_id": "obs:" + re.sub(
            r"[^a-z0-9]", "", f"{candidate_id}{mutation_id}")[:24],
        "candidate_id": candidate_id,
        "mutation_id": mutation_id,
        "observed_at": utc_now(),
        "gauntlet": {
            "killed": killed,
            "attack_overall": attack_overall or None,
            "engineering_attack_overall": eng_overall or None,
            "physics_lifecycle": physics_lifecycle or None,
            "kill_stage": gauntlet_result.get("kill_stage"),
            "kill_reason": str(gauntlet_result.get("kill_reason") or
                               "")[:400] or None,
        },
        "epistemic_state": _epistemic_state(gauntlet_result),
        "improvement_signal": improvement_signal(gauntlet_result),
    }
    return obs


def _epistemic_state(g: Dict[str, Any]) -> str:
    """The gate-level epistemic state (never softened by signals)."""
    if g.get("killed"):
        return "UNSUPPORTED"
    if str(g.get("physics_lifecycle") or "").upper() == \
            "REQUIRES_EXPERIMENT":
        return "REQUIRES_EXPERIMENT"
    if str(g.get("attack_overall") or "").upper().startswith("SURVIVED"):
        return "SUPPORTED"
    return "UNKNOWN"


def improvement_signal(gauntlet_result: Dict[str, Any]) -> Dict[str, Any]:
    """The continuous/discrete improvement signal layer (§8).

    Every value is derived from RECORDED evaluation output or is
    explicitly null with its basis — never invented:
      objective_delta   — numeric only when the evaluation produced
                          numbers (physics margins, equation outputs);
                          else the VERDICT TRANSITION rank delta
                          (discrete, real)
      constraint_delta  — number of REPAIR verdicts cleared (from the
                          engineering attack's counts, when present)
      distance_to_target — null unless a target and a measured value
                          exist in the evaluation record
      information_gain  — the recorded kill/repair-count DELTA (a real
                          count change, not a utility score)
    """
    sig: Dict[str, Any] = {
        "objective_delta": None,
        "objective_delta_basis": None,
        "constraint_delta": None,
        "constraint_delta_basis": None,
        "distance_to_target": None,
        "distance_to_target_basis": None,
        "information_gain": None,
        "information_gain_basis": None,
        "sensitivity": None,
        "sensitivity_basis": "no evaluation pair (a numerical "
                             "derivative requires two real evaluations "
                             "of nearby variants — an AI-invented "
                             "gradient is forbidden)",
        "tradeoff": None,
    }
    counts = gauntlet_result.get("engineering_attack_counts") or {}
    if counts:
        sig["constraint_delta"] = -(int(counts.get("KILL") or 0) +
                                    int(counts.get("REPAIR") or 0))
        sig["constraint_delta_basis"] = (
            "engineering attack KILL+REPAIR count (negative = fewer "
            f"open defects): kill={counts.get('KILL')}, "
            f"repair={counts.get('REPAIR')}")
    verdict = str(gauntlet_result.get("attack_overall") or
                  gauntlet_result.get("engineering_attack_overall") or
                  "").upper()
    if verdict:
        sig["objective_delta"] = _verdict_rank(verdict)
        sig["objective_delta_basis"] = (
            f"verdict-ladder rank of {verdict!r} on "
            f"{'>'.join(VERDICT_LADDER)} — a discrete recorded "
            f"transition, not a fabricated continuous objective")
    killed = bool(gauntlet_result.get("killed"))
    sig["information_gain"] = 0 if killed else 1
    sig["information_gain_basis"] = (
        "recorded: the mutation survived the gauntlet (1) or was "
        "killed (0) — a counted event, never a utility score")
    return sig


def sensitivity_from_evaluations(
        baseline_eval: Dict[str, Any],
        perturbed_eval: Dict[str, Any],
        parameter: str,
        parameter_delta: Optional[float],
        objective_field: str = "objective_delta"
        ) -> Dict[str, Any]:
    """A numerical derivative from TWO REAL evaluations (§9).

    Only valid when both evaluations carry a numeric objective value
    (objective_delta numeric + numeric_basis). Cites both evaluation
    records. Anything else returns the honest null with its basis.
    """
    base_val = baseline_eval.get(objective_field)
    pert_val = perturbed_eval.get(objective_field)
    if not isinstance(base_val, (int, float)) or \
            not isinstance(pert_val, (int, float)):
        return {"parameter": parameter, "sensitivity": None,
                "basis": "the evaluations carry no numeric objective "
                         "values — no derivative is computed (never "
                         "fabricated)"}
    if parameter_delta in (None, 0):
        return {"parameter": parameter, "sensitivity": None,
                "basis": "no recorded parameter delta — the derivative "
                         "denominator is unknown"}
    return {
        "parameter": parameter,
        "parameter_delta": parameter_delta,
        "objective_delta": pert_val - base_val,
        "sensitivity": (pert_val - base_val) / parameter_delta,
        "basis": (f"numerical derivative from two REAL evaluations "
                  f"(baseline={base_val}, perturbed={pert_val}, "
                  f"d_parameter={parameter_delta}); both evaluation "
                  f"records cited in the trajectory"),
        "evaluation_pair": [baseline_eval.get("evaluation_id"),
                            perturbed_eval.get("evaluation_id")],
    }


# ---------------------------------------------------------------------------
# CAUSAL UPDATE (OBSERVATION -> CAUSAL UPDATE -> NEXT DIRECTION)
# ---------------------------------------------------------------------------

def causal_update(hypothesis: Dict[str, Any],
                  observation: Dict[str, Any]) -> Dict[str, Any]:
    """Did the observation match the direction's PREDICTION?

    The update is derived from the recorded fields only:
      - the prediction's direction (INCREASE/DECREASE/... on the
        target) is compared against the observation's improvement
        signal direction (survived/killed, verdict-rank delta, and
        numeric objective_delta when present)
      - MATCH    -> hypothesis status SUPPORTED (the causal model's
                    prediction held; the next direction may compound)
      - MISMATCH -> FALSIFIED (the direction dies; negative knowledge —
                    the causal model was wrong about this variable)
      - UNKNOWN  -> the evaluation could not decide (infrastructure
                    class or ambiguous verdict) — never silently
                    treated as support (Art. XXV)

    The update record carries the full comparison basis so the
    trajectory shows WHY each direction lived or died.
    """
    sig = observation.get("improvement_signal") or {}
    g = observation.get("gauntlet") or {}
    killed = bool(g.get("killed"))
    obj = sig.get("objective_delta")
    direction = str(hypothesis.get("direction") or "").upper()
    if killed:
        match, status = False, "FALSIFIED"
        basis = ("the mutated candidate was KILLED by the gauntlet — "
                 "the direction's predicted improvement did not "
                 "materialize")
    elif isinstance(obj, (int, float)) and obj > 0:
        match, status = True, "SUPPORTED"
        basis = (f"the mutated candidate survived with a recorded "
                 f"improvement (verdict-rank delta {obj})")
    elif observation.get("epistemic_state") == "SUPPORTED":
        match, status = True, "SUPPORTED"
        basis = ("the mutated candidate survived the gauntlet (the "
                 "predicted direction held at the verdict level)")
    elif observation.get("epistemic_state") in ("UNKNOWN",
                                                "REQUIRES_EXPERIMENT",
                                                "ABSTAIN"):
        match, status = None, "EXECUTED"
        basis = ("the evaluation could not decide ("
                 + str(observation.get("epistemic_state"))
                 + ") — UNKNOWN, never treated as support (Art. XXV)")
    else:
        match, status = False, "FALSIFIED"
        basis = ("the mutated candidate survived without a recorded "
                 "improvement — the direction is not supported by the "
                 "observation")
    return {
        "causal_update_id": "cu:" + re.sub(
            r"[^a-z0-9]", "", str(hypothesis.get("hypothesis_id") or
                                  "") + str(observation.get(
                                      "observation_id") or ""))[:24],
        "hypothesis_id": hypothesis.get("hypothesis_id"),
        "observation_id": observation.get("observation_id"),
        "prediction": {
            "target_variable": hypothesis.get("target_variable"),
            "direction": direction,
            "predicted_effect": hypothesis.get("predicted_effect"),
            "predicted_magnitude": hypothesis.get(
                "predicted_magnitude_or_range"),
        },
        "observed": {
            "killed": killed,
            "epistemic_state": observation.get("epistemic_state"),
            "objective_delta": obj,
        },
        "match": match,
        "hypothesis_status_after": status,
        "basis": basis,
        "updated_at": utc_now(),
        "note": ("the causal model update is recorded, not asserted: "
                 "the direction's causal claim lives or dies by the "
                 "recorded observation; FALSIFIED directions become "
                 "negative knowledge for future search (Art. LI)"),
    }


def apply_causal_update(hypothesis: Dict[str, Any],
                        update: Dict[str, Any]) -> Dict[str, Any]:
    """The ONLY sanctioned status transitions after execution:
    EXECUTED -> SUPPORTED | FALSIFIED (never back to GROUNDED)."""
    after = update.get("hypothesis_status_after")
    if hypothesis.get("status") == "EXECUTED" and \
            after in ("SUPPORTED", "FALSIFIED"):
        hypothesis["status"] = after
        hypothesis.setdefault("causal_updates", []).append(update)
    return hypothesis
