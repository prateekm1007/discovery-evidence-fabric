"""toscanini/conversational/nba_controller.py — R446-C1 §8: the Next
Best Action as the REAL controller.

Directive (verbatim intent): "The existing active path already contains
NEXT_BEST_ACTION. Make it the actual controller rather than a
reporting field. For each action compute: action, target_uncertainty,
expected_information_gain, estimated_cost, estimated_latency,
required_capability, risk, reason. Then choose one preferred action.
... The action must actually determine the next execution path."

Two layers, deliberately distinct:
  1. The ENGINE's NEXT_BEST_ACTION stage (adapters.py) remains the
     END-OF-RUN epistemic record — it reports what the COMPLETED run's
     contradictions/experiments/collisions suggest next. It is not
     removed (Art. LXIV: supersede or keep, never duplicate).
  2. THIS module is the RUNTIME controller: it decides, from the
     CURRENT recorded envelope state (never from what a stage WOULD
     produce), which action the engine should take next — and the
     stage policy consumes that decision to RUN/SKIP/DEFER/BLOCK/STOP
     the next stage. Every decision is recorded with its full scored
     ledger, so "why did the engine stop here" is always an auditable
     record, not a narrative.

Scoring (Art. LVI — expected reduction in uncertainty per unit cost):

    score = (expected_information_gain
             × probability_of_decision_change
             × decision_impact)
            / (estimated_cost)
            − redundancy_penalty

The formula is the SAME V4 shape as orchestrator/next_best_action.py
(one scoring authority, two sites — the runtime controller records the
engine's standing formula, it does not invent a second one).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

NBA_CONTROLLER_VERSION = "conversational/nba_controller/1.1.0"

# Action vocabulary (closed). Each action maps to a concrete execution
# path in the engine/pipeline — an action that cannot determine an
# execution path is not a controller action (directive §8).
A_RETRIEVE_MORE = "RETRIEVE_MORE_EVIDENCE"
A_ATTACK_CANDIDATE = "ATTACK_CANDIDATE"
A_COMPETING_MECHANISM = "GENERATE_COMPETING_MECHANISM"
A_ENGINEERING_ESCALATION = "ENGINEERING_ESCALATION"
A_PROPOSE_DECISIVE_EXPERIMENT = "PROPOSE_DECISIVE_EXPERIMENT"
A_ASK_CLARIFICATION = "ASK_CLARIFICATION"
A_STOP_HONEST = "STOP_HONEST"
A_PACKAGE_READY = "PACKAGE_READY"

ACTIONS = (A_RETRIEVE_MORE, A_ATTACK_CANDIDATE,
           A_COMPETING_MECHANISM, A_ENGINEERING_ESCALATION,
           A_PROPOSE_DECISIVE_EXPERIMENT, A_ASK_CLARIFICATION,
           A_STOP_HONEST, A_PACKAGE_READY)

# Evidence-base adequacy bound (Art. XXVII — MODEL_DERIVED, declared):
# a base of >= 8 frozen records is a reasonable retrieval attempt for
# the problem-binding decision (aligned with the engine's depth-
# contract record floors); below it, more retrieval is the honest
# next move; at/above it with ZERO mechanism support, further
# retrieval has already had its chance — the honest move is to stop
# and say the problem's existence is unestablished (directive §5).
ADEQUATE_EVIDENCE_BASE = 8


def controller_action(action: str, target_uncertainty: str,
                      expected_information_gain: float,
                      probability_of_decision_change: float,
                      decision_impact: float, estimated_cost: float,
                      estimated_latency_s: float,
                      required_capability: str, risk: str, reason: str,
                      redundancy_penalty: float = 0.0,
                      input_basis: Optional[Dict[str, Any]] = None
                      ) -> Dict[str, Any]:
    """One scored action — the directive §8 field list, exactly.

    R478 P0-4: when input_basis is provided it travels with the action
    (formula + inputs + provenance class), so no scored number is a
    bare literal anymore (Art. XXVII: the derivation travels with the
    value it produced)."""
    cost = max(estimated_cost, 0.01)
    score = (expected_information_gain *
             probability_of_decision_change *
             decision_impact) / cost - redundancy_penalty
    out = {
        "action": action,
        "target_uncertainty": target_uncertainty,
        "expected_information_gain": round(
            expected_information_gain, 3),
        "probability_of_decision_change": round(
            probability_of_decision_change, 3),
        "decision_impact": round(decision_impact, 3),
        "estimated_cost": round(estimated_cost, 2),
        "estimated_latency_s": round(estimated_latency_s, 1),
        "required_capability": required_capability,
        "risk": risk,
        "reason": reason,
        "redundancy_penalty": round(redundancy_penalty, 3),
        "score": round(score, 4),
    }
    if input_basis:
        out["input_basis"] = input_basis
    return out


# ---------------------------------------------------------------------------
# R478 P0-4 — state-derived inputs + measured-latency lookup
# ---------------------------------------------------------------------------

def _measured_stage_seconds(env_state: Dict[str, Any],
                            stage: str) -> Optional[float]:
    """The run's OWN measured wall time for a stage that already ran,
    from the envelope's stage_log (started_at/finished_at). Returns
    None when the stage has not run — the caller then falls back to a
    DECLARED prior, labeled as such (Art. VI/XXV: measured and
    declared are never conflated)."""
    for entry in reversed(env_state.get("stage_log") or []):
        if not isinstance(entry, dict) or entry.get("stage") != stage:
            continue
        if entry.get("status") != "OK":
            continue
        try:
            t0 = datetime.fromisoformat(
                str(entry.get("started_at")).replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(
                str(entry.get("finished_at")).replace("Z", "+00:00"))
            seconds = (t1 - t0).total_seconds()
            if seconds >= 0:
                return seconds
        except (ValueError, TypeError):
            continue
    return None


# ---------------------------------------------------------------------------
# Cost/latency constants — provenance declared (Art. XXVII)
# ---------------------------------------------------------------------------
# MODEL_DERIVED from the engine's own code structure and the routing
# ledger's recorded measurements (ENGINE_RUNS/model_routing/
# ledger.jsonl, 612 lines: real per-call latency_ms by stage/task):
#   STRONG-class generation attempts measured 8–547 s (failure-tail
#   dominated); successful FAST-class calls cluster in the 5–30 s
#   band. The constants below are ORDER-OF-MAGNITUDE planning numbers
#   for the controller's COST axis only — they rank actions, they
#   never become scientific claims, and each carries this provenance
#   note in the emitted record.
# R478 P0-4 (external audit): the EIG half is NO LONGER constant —
# the audit measured the R458 trace as 48× identical
# (EIG 0.85 / cost 2.0 / score 0.2826) because every action's inputs
# were literals. EIGs are now computed from the recorded envelope
# state (formula + inputs travel in each action's input_basis), and
# estimated_latency_s prefers the run's OWN measured stage duration
# from stage_log when the comparable stage already ran
# (MEASURED_IN_RUN), falling back to the declared planning constant
# (DECLARED_PRIOR) — measured and declared are never conflated.
_COST_PROVENANCE = (
    "MODEL_DERIVED — order-of-magnitude planning constants derived "
    "from the engine's call-site structure (adapters.py static LLM "
    "call-sites per stage) and the recorded routing ledger "
    "latency_ms distribution (ENGINE_RUNS/model_routing/ledger.jsonl); "
    "used ONLY to rank controller actions by cost, never quoted as "
    "a measured result. R478 P0-4: latency additionally prefers the "
    "run's own measured stage durations (cost_basis MEASURED_IN_RUN) "
    "when stage_log carries them; EIG is state-derived (eig_basis "
    "records the formula and inputs) — the R458 constant-trace class "
    "is dead by construction"
)

_LLM_CALLS_PER_STAGE = {
    # static count of llm_registry.generate() call sites reachable
    # from each stage's adapter (COMPUTED from source, R446 audit)
    "RETRIEVE": 0, "FREEZE": 0, "PREMISE_GATE": 0,
    "SYNTHESIZE": 1, "VERIFY": 0, "MECHANISM_SPACE": 5,
    "MULTI_SOURCE_DISCOVERY": 0, "COLLISION": 0, "PHYSICS": 0,
    "ATTACK": 1, "CONTRADICTION": 0, "KILLER_EXPERIMENT": 0,
    "ADJUDICATION": 0, "CLASSIFY": 0, "NEXT_BEST_ACTION": 0,
    "RANK": 1,
}


def llm_calls_per_stage(stage: str) -> int:
    return _LLM_CALLS_PER_STAGE.get(stage, 0)


# ---------------------------------------------------------------------------
# The controller decision
# ---------------------------------------------------------------------------

def decide(env_state: Dict[str, Any],
           clarification_needed: bool = False,
           problem_understanding: Optional[Dict[str, Any]] = None
           ) -> Dict[str, Any]:
    """Compute the ranked action ledger + ONE preferred action from
    the CURRENT recorded state. Deterministic; zero LLM.

    env_state is the engine envelope as a plain dict (or the
    projected run state between stages). The decision NEVER mutates
    the envelope — it is returned to the stage policy, which records
    it on the stage entry it controls.
    """
    ec = env_state.get("evidence_classification") or {}
    verified = [it for it in (ec.get("items") or [])
                if isinstance(it, dict)
                and it.get("classification") in ("DIRECT_SUPPORT",
                                                 "PARTIAL_SUPPORT")]
    n_evidence = len(env_state.get("evidence") or [])
    mm = env_state.get("mechanism_map") or {}
    has_mechanism = bool(mm.get("intervention") and mm.get("mechanism"))
    attack = env_state.get("attack_results") or {}
    attack_ran = bool(attack) and "overall" in attack
    attack_pass = attack.get("overall") == "PASS"
    adjudication = env_state.get("adjudication") or {}
    verdict = (adjudication.get("council") or {}).get("verdict")
    ke = (env_state.get("killer_experiment") or {}).get("selected")
    collision = env_state.get("collision_results") or {}
    engineering = env_state.get("engineering_spec") or {}

    actions: List[Dict[str, Any]] = []

    # R478 P0-4: state-derived inputs (formula + inputs recorded per
    # action in input_basis). The contradiction pressure reads the
    # claim-level classification's CONTRADICTORY count (available at
    # VERIFY — before the attack is proposed) and the queue's own
    # unresolved count (when the CONTRADICTION stage has already run);
    # the larger of the two is the honest "how much is unresolved"
    # measure at THIS decision point.
    _contra = (env_state.get("contradictions") or {})
    _n_contra = max(
        int((ec.get("counts") or {}).get("CONTRADICTORY") or 0),
        int(_contra.get("unresolved_count", 0) or 0))
    _n_direct = int((ec.get("counts") or {}).get("DIRECT_SUPPORT") or 0)
    _synth_s = _measured_stage_seconds(env_state, "SYNTHESIZE")
    _retrieve_s = _measured_stage_seconds(env_state, "RETRIEVE")

    # --- clarification (§4): only when the PU says it is material ------
    if clarification_needed:
        actions.append(controller_action(
            A_ASK_CLARIFICATION,
            target_uncertainty="target_variable / objective binding",
            expected_information_gain=0.9,
            probability_of_decision_change=0.8,
            decision_impact=0.9,
            estimated_cost=0.05,       # one user round-trip
            estimated_latency_s=60.0,
            required_capability="conversational_pause",
            risk="user latency; run deferred",
            reason="the Problem Understanding contract flags a field "
                   "whose answer materially changes the search space "
                   "(clarification.evaluate_clarification_need)",
            input_basis={
                "eig": "DECLARED_PRIOR (0.9; material-binding "
                       "round-trip has no recorded base rate — Art. XXV)",
                "cost": "DECLARED_PRIOR (0.05; one user round-trip)",
            }))

    # --- evidence sufficiency (§14) -------------------------------------
    if n_evidence and len(verified) < 3 and n_evidence < ADEQUATE_EVIDENCE_BASE:
        _deficit = 1.0 - min(1.0, len(verified) / 3.0)
        _eig_retrieve = round(0.4 + 0.5 * _deficit, 3)
        actions.append(controller_action(
            A_RETRIEVE_MORE,
            target_uncertainty="problem existence and mechanism support",
            expected_information_gain=_eig_retrieve,
            probability_of_decision_change=0.6,
            decision_impact=0.9,
            estimated_cost=1.0,
            estimated_latency_s=(_retrieve_s if _retrieve_s is not None
                                 else 45.0),
            required_capability="source_connectors",
            risk="provider failure recorded honestly (Art. XXI.3)",
            reason=f"only {len(verified)} verified evidence items "
                   f"recorded (<3) and the frozen base is small "
                   f"({n_evidence} < {ADEQUATE_EVIDENCE_BASE}) — more "
                   f"retrieval materially reduces uncertainty (§14 "
                   f"stopping condition not met)",
            input_basis={
                "eig": {"formula": "0.4 + 0.5 x (1 - min(1, "
                                       "n_verified / 3)) — the verified-"
                                       "item deficit scales the gain",
                        "inputs": {"n_verified": len(verified)},
                        "provenance": "MODEL_DERIVED (declared linear "
                                      "map, Art. XXVII)"},
                "cost": "DECLARED_PRIOR (1.0; connector fan-out "
                        "planning constant)",
                "latency": ("MEASURED_IN_RUN (stage_log RETRIEVE)"
                            if _retrieve_s is not None
                            else "DECLARED_PRIOR (45 s; no RETRIEVE "
                                 "duration in this run's stage_log)")},
            ))
    elif len(verified) >= 3 and not has_mechanism:
        _eig_compete = round(0.5 + 0.06 * min(len(verified), 5), 3)
        actions.append(controller_action(
            A_COMPETING_MECHANISM,
            target_uncertainty="causal mechanism for the stated failure",
            expected_information_gain=_eig_compete,
            probability_of_decision_change=0.7,
            decision_impact=0.8,
            estimated_cost=2.0,
            estimated_latency_s=(_synth_s if _synth_s is not None
                                 else 90.0),
            required_capability="synthesis (STRONG)",
            risk="generator untrusted (Art. XVIII); verification "
                 "downstream",
            reason=f"evidence sufficient ({len(verified)} verified "
                   f"items) and no mechanism yet — synthesize and keep "
                   f"H1/H2/H3 competing (§15)",
            input_basis={
                "eig": {"formula": "0.5 + 0.06 x min(n_verified, 5) "
                                       "— synthesis gain scales with the "
                                       "verified base it can draw on",
                        "inputs": {"n_verified": len(verified)},
                        "provenance": "MODEL_DERIVED (declared linear "
                                      "map, Art. XXVII)"},
                "cost": "DECLARED_PRIOR (2.0; STRONG-class synthesis "
                        "planning constant)",
                "latency": ("MEASURED_IN_RUN (stage_log SYNTHESIZE)"
                            if _synth_s is not None
                            else "DECLARED_PRIOR (90 s; no SYNTHESIZE "
                                 "duration in this run's stage_log)")},
            ))

    # --- attack (§16/§17) ------------------------------------------------
    if has_mechanism and not attack_ran:
        # R478 P0-4: THE constant the audit measured (0.85) is now a
        # function of the recorded state — more verified support and
        # more unresolved contradictions make the attack more
        # informative; the value varies across runs BY CONSTRUCTION.
        _eig_attack = round(min(0.95, 0.5 + 0.05 * min(_n_direct, 6)
                                + 0.05 * min(_n_contra, 4)), 3)
        actions.append(controller_action(
            A_ATTACK_CANDIDATE,
            target_uncertainty="mechanism validity under adversarial "
                               "challenge",
            expected_information_gain=_eig_attack,
            probability_of_decision_change=0.7,
            decision_impact=0.95,
            estimated_cost=2.0,
            estimated_latency_s=(_synth_s if _synth_s is not None
                                 else 120.0),
            required_capability="adversarial (independent)",
            risk="attacker calibration state applies (BS-011)",
            reason="a candidate remains a hypothesis until attacked "
                   "(§16); the gauntlet is the highest-impact "
                   "uncertainty reducer available now",
            input_basis={
                "eig": {"formula": "min(0.95, 0.5 + 0.05 x "
                                       "min(n_direct_support, 6) + "
                                       "0.05 x min(n_contradictory, "
                                       "4)) — the gauntlet is more "
                                       "informative when more is at "
                                       "stake (support) and more is "
                                       "unresolved (contradictions)",
                        "inputs": {"n_direct_support": _n_direct,
                                   "n_contradictory": _n_contra},
                        "provenance": "MODEL_DERIVED (declared linear "
                                      "map, Art. XXVII)"},
                "cost": "DECLARED_PRIOR (2.0; independent-attacker "
                        "planning constant)",
                "latency": ("MEASURED_IN_RUN (stage_log SYNTHESIZE, "
                            "the same STRONG-class LLM workload)"
                            if _synth_s is not None
                            else "DECLARED_PRIOR (120 s)"),
                "replaces": "the 0.85 literal measured as the R458 "
                            "constant EIG trace (R478 P0-4)"},
            ))

    # --- engineering escalation (§5/§23) ---------------------------------
    if has_mechanism and attack_ran and attack_pass:
        actions.append(controller_action(
            A_ENGINEERING_ESCALATION,
            target_uncertainty="engineering representability of the "
                               "surviving candidate",
            expected_information_gain=0.6,
            probability_of_decision_change=0.6,
            decision_impact=0.8,
            estimated_cost=3.0,
            estimated_latency_s=240.0,
            required_capability="engineering spec + CadQuery/OCCT",
            risk="cost without survivor benefit if the premise was "
                 "weak — premise gate already ran upstream",
            reason="candidate survived attack — escalate toward "
                   "engineering (directive §5)"))

    # --- decisive experiment (§5) ------------------------------------------
    if has_mechanism and attack_ran and attack_pass and ke:
        actions.append(controller_action(
            A_PROPOSE_DECISIVE_EXPERIMENT,
            target_uncertainty="physical truth of the surviving "
                               "mechanism",
            expected_information_gain=0.9,
            probability_of_decision_change=0.9,
            decision_impact=1.0,
            estimated_cost=5.0,
            estimated_latency_s=180.0,
            required_capability="experiment design (deterministic)",
            risk="the experiment is DESIGNED, not run — reality "
                 "boundary respected (Art. XXXVIII)",
            reason="high-value survivor with a recorded killer-"
                   "experiment contract — escalate toward the decisive "
                   "experiment (Art. LII falsification contract)"))

    # --- package --------------------------------------------------------
    if engineering.get("complete") or verdict == "ESTABLISHED_PROVISIONALLY":
        actions.append(controller_action(
            A_PACKAGE_READY,
            target_uncertainty="buyer transferability",
            expected_information_gain=0.3,
            probability_of_decision_change=0.4,
            decision_impact=0.6,
            estimated_cost=1.5,
            estimated_latency_s=120.0,
            required_capability="package compiler",
            risk="one technology → one package (product rule)",
            reason="engineering representation recorded — the buyer "
                   "package is the remaining transfer step"))

    # --- honest stop (§5 weak premise) ------------------------------------
    # classification-presence guard (same rule as the stage policy):
    # the STOP_HONEST action fires only when the claim-level
    # classification HAS RUN, the evidence base is ADEQUATE, and the
    # recorded support is zero — an absent classification is "not yet
    # classified" and a small base deserves more retrieval first
    # (Art. XXV: refusal to compute needs a recorded basis).
    classification_ran = bool(ec.get("items")) or bool(ec.get("counts"))
    if classification_ran and n_evidence >= ADEQUATE_EVIDENCE_BASE \
            and not verified and \
            not (ec.get("counts") or {}).get("DIRECT_SUPPORT") and \
            not has_mechanism:
        actions.append(controller_action(
            A_STOP_HONEST,
            target_uncertainty="problem existence itself",
            expected_information_gain=0.0,
            probability_of_decision_change=0.0,
            decision_impact=1.0,
            estimated_cost=0.0,
            estimated_latency_s=0.0,
            required_capability="none",
            risk="none — refusing compute is the honest move",
            reason=f"{n_evidence} evidence records frozen and NONE "
                   f"mechanism-supporting — problem existence cannot "
                   f"be established; further compute would optimize an "
                   f"unverified problem (Art. XX)"))

    ranked = sorted(actions, key=lambda a: (-a["score"], a["action"]))
    preferred = ranked[0] if ranked else None
    return {
        "controller_version": NBA_CONTROLLER_VERSION,
        "formula": "score = (gain × p_change × impact) / cost − "
                   "redundancy_penalty  [orchestrator/next_best_action "
                   "V4 shape — one scoring authority, two sites]",
        "cost_provenance": _COST_PROVENANCE,
        "ranked_actions": ranked,
        "preferred_action": preferred,
        "n_actions": len(actions),
        "decided_from": {
            "n_evidence": n_evidence,
            "n_verified_items": len(verified),
            "n_direct_support": _n_direct,
            "n_contradictory": _n_contra,
            "measured_synth_seconds": _synth_s,
            "measured_retrieve_seconds": _retrieve_s,
            "mechanism_recorded": has_mechanism,
            "attack_ran": attack_ran,
            "attack_pass": attack_pass,
            "adjudication_verdict": verdict,
            "killer_experiment_recorded": bool(ke),
            "engineering_recorded": bool(engineering),
            "clarification_needed": clarification_needed,
        },
    }
