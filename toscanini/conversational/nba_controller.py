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

from typing import Any, Dict, List, Optional

NBA_CONTROLLER_VERSION = "conversational/nba_controller/1.0.0"

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
                      redundancy_penalty: float = 0.0
                      ) -> Dict[str, Any]:
    """One scored action — the directive §8 field list, exactly."""
    cost = max(estimated_cost, 0.01)
    score = (expected_information_gain *
             probability_of_decision_change *
             decision_impact) / cost - redundancy_penalty
    return {
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
_COST_PROVENANCE = (
    "MODEL_DERIVED — order-of-magnitude planning constants derived "
    "from the engine's call-site structure (adapters.py static LLM "
    "call-sites per stage) and the recorded routing ledger "
    "latency_ms distribution (ENGINE_RUNS/model_routing/ledger.jsonl); "
    "used ONLY to rank controller actions by cost, never quoted as "
    "a measured result"
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
                   "(clarification.evaluate_clarification_need)"))

    # --- evidence sufficiency (§14) -------------------------------------
    if n_evidence and len(verified) < 3 and n_evidence < ADEQUATE_EVIDENCE_BASE:
        actions.append(controller_action(
            A_RETRIEVE_MORE,
            target_uncertainty="problem existence and mechanism support",
            expected_information_gain=0.7,
            probability_of_decision_change=0.6,
            decision_impact=0.9,
            estimated_cost=1.0,
            estimated_latency_s=45.0,
            required_capability="source_connectors",
            risk="provider failure recorded honestly (Art. XXI.3)",
            reason=f"only {len(verified)} verified evidence items "
                   f"recorded (<3) and the frozen base is small "
                   f"({n_evidence} < {ADEQUATE_EVIDENCE_BASE}) — more "
                   f"retrieval materially reduces uncertainty (§14 "
                   f"stopping condition not met)"))
    elif len(verified) >= 3 and not has_mechanism:
        actions.append(controller_action(
            A_COMPETING_MECHANISM,
            target_uncertainty="causal mechanism for the stated failure",
            expected_information_gain=0.8,
            probability_of_decision_change=0.7,
            decision_impact=0.8,
            estimated_cost=2.0,
            estimated_latency_s=90.0,
            required_capability="synthesis (STRONG)",
            risk="generator untrusted (Art. XVIII); verification "
                 "downstream",
            reason=f"evidence sufficient ({len(verified)} verified "
                   f"items) and no mechanism yet — synthesize and keep "
                   f"H1/H2/H3 competing (§15)"))

    # --- attack (§16/§17) ------------------------------------------------
    if has_mechanism and not attack_ran:
        actions.append(controller_action(
            A_ATTACK_CANDIDATE,
            target_uncertainty="mechanism validity under adversarial "
                               "challenge",
            expected_information_gain=0.85,
            probability_of_decision_change=0.7,
            decision_impact=0.95,
            estimated_cost=2.0,
            estimated_latency_s=120.0,
            required_capability="adversarial (independent)",
            risk="attacker calibration state applies (BS-011)",
            reason="a candidate remains a hypothesis until attacked "
                   "(§16); the gauntlet is the highest-impact "
                   "uncertainty reducer available now"))

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
            "mechanism_recorded": has_mechanism,
            "attack_ran": attack_ran,
            "attack_pass": attack_pass,
            "adjudication_verdict": verdict,
            "killer_experiment_recorded": bool(ke),
            "engineering_recorded": bool(engineering),
            "clarification_needed": clarification_needed,
        },
    }
