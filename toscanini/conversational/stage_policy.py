"""toscanini/conversational/stage_policy.py — R446-C1 §5/§6/§7: the
adaptive stage execution policy and the canonical non-execution
vocabulary.

Directive §5 (verbatim intent): "Do not automatically execute the full
pipeline. At each meaningful state: CURRENT STATE → UNCERTAINTY →
AVAILABLE ACTIONS → EXPECTED INFORMATION GAIN → COST/LATENCY → NEXT
BEST ACTION. ... This is conditional computation, not removal of
epistemic controls."

Directive §6: every stage can return RUN | SKIP | DEFER | BLOCK | STOP
with a reason and a next action.

Directive §7: NOT_REQUIRED / NOT_REACHED / NOT_RUN / BLOCKED / FAILED /
SKIPPED_LOW_VALUE "should remain distinct canonical states. Do not
compress them for convenience."

Constitutional contract:
  - The ENGINE stage_log statuses remain the authority (Art. X). The
    six-state vocabulary here is the PRODUCT projection + the NEW
    typed policy statuses the engine records when the gate refuses a
    stage. The mapping is one-way and total.
  - A policy SKIP is a RECORDED refusal (Art. XXV) — never an absence
    claim, never a scientific verdict (Art. LXI).
  - Epistemic controls are NOT removed: stages whose result the chain
    constitutionally consumes (evidence freeze, premise gate, attack,
    adjudication) are NEVER skippable for cost reasons. The policy may
    only refuse compute that the CURRENT RECORDED STATE makes
    redundant or pointless — every refusal carries the measured
    prerequisite evidence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from toscanini.conversational import nba_controller

POLICY_VERSION = "conversational/stage_policy/1.0.0"

# ---------------------------------------------------------------------------
# §6 decisions (closed vocabulary)
# ---------------------------------------------------------------------------
RUN = "RUN"
SKIP = "SKIP"
DEFER = "DEFER"
BLOCK = "BLOCK"
STOP = "STOP"
DECISIONS = (RUN, SKIP, DEFER, BLOCK, STOP)

# ---------------------------------------------------------------------------
# §7 non-execution states (closed vocabulary) + the total one-way
# mapping FROM engine/bridge statuses.
# ---------------------------------------------------------------------------
NOT_REQUIRED = "NOT_REQUIRED"          # not applicable to this decision
NOT_REACHED = "NOT_REACHED"            # the run ended before this stage
NOT_RUN = "NOT_RUN"                    # on the path; no verdict exists
BLOCKED = "BLOCKED"                    # explicit blocker; resumable
FAILED = "FAILED"                      # executed and failed
SKIPPED_LOW_VALUE = "SKIPPED_LOW_VALUE"  # info gain below cost (policy)

NON_EXECUTION_STATES = (NOT_REQUIRED, NOT_REACHED, NOT_RUN, BLOCKED,
                        FAILED, SKIPPED_LOW_VALUE)

# engine/bridge status → canonical non-execution state. Total: any
# status not mapping to a non-execution state is an EXECUTION state.
STATUS_MAP = {
    # engine stage_log statuses
    "DISABLED_BY_CONFIG": NOT_REQUIRED,
    "SKIPPED_UPSTREAM_FAILURE": NOT_REACHED,
    "SKIPPED_ADMISSION": NOT_REQUIRED,
    # R446-C1 policy statuses (recorded by the stage gate)
    "SKIPPED_POLICY_LOW_VALUE": SKIPPED_LOW_VALUE,
    "SKIPPED_POLICY_NOT_REQUIRED": NOT_REQUIRED,
    "BLOCKED_POLICY": BLOCKED,
    "STOPPED_POLICY": NOT_REACHED,     # the STOP point itself is honest:
    # the stage did not run and the loop halted here (reason recorded)
    "DEFERRED_POLICY": NOT_RUN,        # postponed; no verdict exists
    # bridge / visual vocabulary (R441–R443 precedents)
    "NOT_RUN": NOT_RUN,
    "RENDER_SKIPPED_LOW_MEMORY": BLOCKED,
    "SKIPPED_INFRA_UNAVAILABLE": BLOCKED,
    "FAILED_EXPLICIT": FAILED,
}

# Stage classes: what may NEVER be refused by policy (the epistemic
# core — evidence, premise, verification, attack, adjudication) vs the
# policy-admissible compute sites.
_UNSKIPPABLE = frozenset({
    "RETRIEVE", "FREEZE", "PREMISE_GATE", "VERIFY",
    "ATTACK", "ADJUDICATION", "CLASSIFY",
})


def project_non_execution(status: str) -> Optional[str]:
    """One-way total mapping: engine/bridge status → the §7 canonical
    non-execution state (None = an execution state)."""
    return STATUS_MAP.get((status or "").upper())


def stage_decision(stage: str, decision: str, reason: str,
                   next_action: Optional[str] = None,
                   skip_class: Optional[str] = None,
                   evidence: Optional[Dict[str, Any]] = None
                   ) -> Dict[str, Any]:
    """§6 contract object: {decision, stage, reason, next_action} with
    the typed skip class (§7) and the prerequisite evidence the
    decision rested on."""
    return {
        "policy_version": POLICY_VERSION,
        "stage": stage,
        "decision": decision,
        "reason": reason,
        "next_action": next_action,
        "skip_class": skip_class,
        "prerequisite_evidence": evidence or {},
    }


# ---------------------------------------------------------------------------
# Evidence-sufficiency rule (§14: retrieval stopping)
# ---------------------------------------------------------------------------

# Directive §14: "sufficient independent evidence for the decision."
# Threshold provenance (Art. XXVII): MODEL_DERIVED from the engine's
# own standing contracts — the stage-entry VERIFIED_EVIDENCE
# prerequisite requires >=1 verified item for candidate generation
# (R399 W2.3); two distinct source families is the engine's
# independence vocabulary (Art. XXI.7 "genuinely independent
# evidence"). The sufficiency bound for STOPPING retrieval is >=3
# verified items across >=2 families: enough to attempt synthesis
# with redundancy. Recorded here as the declared, revisable constant
# with its derivation — never drifted silently.
SUFFICIENT_VERIFIED_ITEMS = 3
SUFFICIENT_SOURCE_FAMILIES = 2


def evidence_sufficiency(env_state: Dict[str, Any]) -> Dict[str, Any]:
    """§14 stopping condition: does MORE retrieval materially reduce
    uncertainty? Computed from the envelope's own recorded evidence
    classification (never from search counts alone — Art. XXI)."""
    ec = env_state.get("evidence_classification") or {}
    items = [it for it in (ec.get("items") or [])
             if isinstance(it, dict)
             and it.get("classification") in ("DIRECT_SUPPORT",
                                              "PARTIAL_SUPPORT")]
    families = {str(it.get("source") or it.get("source_family") or
                    it.get("provider") or "unknown")[:60] for it in items}
    sufficient = (len(items) >= SUFFICIENT_VERIFIED_ITEMS
                  and len(families) >= SUFFICIENT_SOURCE_FAMILIES)
    return {
        "sufficient": sufficient,
        "n_verified_items": len(items),
        "n_source_families": len(families),
        "source_families": sorted(families),
        "thresholds": {
            "verified_items": SUFFICIENT_VERIFIED_ITEMS,
            "source_families": SUFFICIENT_SOURCE_FAMILIES,
            "provenance": "MODEL_DERIVED — R399 W2.3 verified-evidence "
                          "prerequisite + Art. XXI.7 independence "
                          "vocabulary (see module docstring)",
        },
        "decision_basis": "more retrieval materially reduces "
                          "uncertainty" if not sufficient else
                          "additional retrieval would not materially "
                          "change the frozen-evidence decision inputs",
    }


# ---------------------------------------------------------------------------
# The engine stage gate (§5/§6) — called by EngineRun before each stage
# ---------------------------------------------------------------------------

def engine_gate(stage: str, env, nba: Optional[Dict[str, Any]] = None
                ) -> Optional[Dict[str, Any]]:
    """The policy decision for ONE engine stage, from the CURRENT
    RECORDED ENVELOPE (never from inference about what would happen).

    Returns None → RUN (the constitutionally-default path: the stage
    is part of the epistemic chain and nothing recorded makes its
    compute redundant). Returns a §6 decision object otherwise.

    §8 wiring: the NBA controller's PREFERRED ACTION is the primary
    input — the gate decides each stage IN THE CONTEXT of the action
    the controller chose. The nba record is computed by the caller
    (the worker's gate closure) via nba_controller.decide(env) so one
    decision serves the whole stage loop; a bare call without it
    falls back to the local rules (same shapes, still deterministic).

    The gate is CONSERVATIVE BY DESIGN: it refuses compute only on
    measured, recorded state; it never refuses an epistemic control
    (the _UNSKIPPABLE set: evidence, premise, verification, attack,
    adjudication — these always RUN when reached on the live path).
    """
    env_state = env.to_dict() if hasattr(env, "to_dict") else (
        env if isinstance(env, dict) else {})
    preferred = ((nba or {}).get("preferred_action") or {}).get("action")

    # -- STOP: problem existence cannot be established -------------------
    # The premise gate is a deterministic instrument that ALWAYS runs;
    # a MALFORMED_OR_FALSE_PREMISE verdict is already a conductor-level
    # fatality (R394 s6). The policy's STOP fires EARLIER for the
    # weak-premise shape the directive names: the premise is coherent
    # but NOTHING in the frozen evidence speaks to the problem — the
    # problem-existence gate (Art. XX) cannot be attempted. Stopping
    # BEFORE candidate-generation compute is the honest move.
    if stage in ("SYNTHESIZE", "MECHANISM_SPACE"):
        premise = env_state.get("premise_gate") or {}
        if premise.get("premise_verdict") == "MALFORMED_OR_FALSE_PREMISE":
            return None   # the conductor already fatality-handles this
        ec = env_state.get("evidence_classification") or {}
        items = [it for it in (ec.get("items") or [])
                 if isinstance(it, dict)
                 and it.get("classification") in ("DIRECT_SUPPORT",
                                                  "PARTIAL_SUPPORT")]
        n_evidence = len(env_state.get("evidence") or [])
        # classification-presence guard: the claim-level classification
        # is produced by the VERIFY stage (AFTER first-pass synthesis),
        # so its ABSENCE at SYNTHESIZE time is "not yet classified" —
        # an honest RUN, never a stop (Art. XXV: absence of the record
        # is not a zero-support verdict). The STOP fires only when the
        # classification HAS run and recorded zero mechanism support
        # (the resumed-run / re-admission shape).
        classification_ran = bool(ec.get("items")) or \
            bool(ec.get("counts"))
        # adequacy bound (Art. XXVII, MODEL_DERIVED — same declared
        # constant as the NBA controller's ADEQUATE_EVIDENCE_BASE): a
        # small base deserves more retrieval, not a stop
        adequate_base = n_evidence >= nba_controller.ADEQUATE_EVIDENCE_BASE
        if stage == "SYNTHESIZE" and classification_ran \
                and adequate_base and not items and \
                not (ec.get("counts") or {}).get("DIRECT_SUPPORT"):
            # evidence exists but ZERO of it supports any mechanism of
            # the stated problem — problem existence unestablished.
            # The NBA controller records the same shape as its
            # STOP_HONEST action (§8: the action determines the path).
            return stage_decision(
                "SYNTHESIZE", STOP,
                "problem existence cannot be established: "
                f"{n_evidence} evidence records frozen, 0 classified as "
                "mechanism-supporting — generating candidates now would "
                "solve an unverified problem (Art. XX problem-"
                "existence gate before mechanism optimization)"
                + (f"; NBA preferred action: {preferred}" if preferred
                   else ""),
                next_action="re-formulate the problem statement with "
                            "the user OR retrieve evidence for the "
                            "actual failure mode",
                evidence={"n_evidence": n_evidence,
                          "n_verified_items": 0,
                          "nba_preferred": preferred})

    # -- SKIP (low value): redundant mechanism-space generation -----------
    # MECHANISM_SPACE is five LLM instantiation calls building a
    # structured mechanism space. When the frozen evidence carries a
    # VERIFIED primary mechanism (synthesis already produced and
    # verified a mechanism) the space's marginal information does not
    # justify the compute — the distinctness authority (Art. XLII) is
    # served by collision + adversarial stages downstream, which still
    # run. Evidence-sufficiency (§14) is the prerequisite.
    if stage == "MECHANISM_SPACE":
        mm = env_state.get("mechanism_map") or {}
        if mm.get("intervention") and mm.get("mechanism"):
            suff = evidence_sufficiency(env_state)
            if suff["sufficient"]:
                return stage_decision(
                    "MECHANISM_SPACE", SKIP,
                    "redundant mechanism-space generation: a verified "
                    "primary mechanism is already recorded and the "
                    "frozen evidence is sufficient "
                    f"({suff['n_verified_items']} verified items, "
                    f"{suff['n_source_families']} source families) — "
                    "distinctness is still enforced downstream by "
                    "COLLISION/ATTACK (unchanged)"
                    + (f"; NBA preferred action: {preferred}" if
                       preferred else ""),
                    next_action="proceed to prior-art collision",
                    skip_class=SKIPPED_LOW_VALUE,
                    evidence={"mechanism_recorded": True,
                              "n_verified_items":
                                  suff["n_verified_items"],
                              "n_source_families":
                                  suff["n_source_families"],
                              "nba_preferred": preferred})

    # -- DEFER: no honest reason to run now, but nothing forbids later ---
    # Reserved shape: a stage whose inputs are not yet recorded but
    # will be produced upstream in THIS run (the engine chain is
    # linear, so defer currently degenerates to RUN-when-reached; the
    # vocabulary is declared so the record format is total from day
    # one — see the audit's honest-limitations section).

    # -- everything else: RUN (None) ---------------------------------------
    return None


# ---------------------------------------------------------------------------
# The post-RANK / expensive-artifact policy (§23 lazy execution)
# ---------------------------------------------------------------------------

def expensive_artifact_policy(env_state: Dict[str, Any],
                              lineage: Optional[Dict[str, Any]] = None
                              ) -> Dict[str, Any]:
    """§23 lazy execution for the expensive tail (engineering spec,
    CAD/geometry, visual package, buyer package): generate only when
    justified by the RECORDED verdicts.

    Refusal grounds (each measured from the run's own records):
      - candidate killed (challenge.killed) → SKIP, NOT_REQUIRED
        ("no CAD, no visual package, no buyer PDF" — directive §23)
      - no retained candidate → SKIP, NOT_REQUIRED
      - synthesis capability-insufficient → BLOCK (resumable infra
        class, Art. LXI — never a scientific rejection)
      - package already complete → SKIP, NOT_REQUIRED (idempotent)
    Otherwise RUN — a surviving candidate escalates toward engineering
    (directive §5), a high-value survivor toward the decisive
    experiment (already designed by KILLER_EXPERIMENT).
    """
    mm = env_state.get("mechanism_map") or {}
    attack = env_state.get("attack_results") or {}
    adjudication = env_state.get("adjudication") or {}

    # killed-invention authority (R452): challenge.killed and evidence
    # verification are AUTHORITATIVE over final_status
    killed = False
    if lineage:
        gens = [g for g in (lineage.get("generations") or [])
                if isinstance(g, dict)]
        cur_gen = (lineage.get("current_invention") or {}).get("gen")
        cur = next((g for g in gens if g.get("gen") == cur_gen),
                   gens[-1] if gens else None)
        if cur and (cur.get("challenge") or {}).get("killed"):
            killed = True
    if attack.get("overall") == "KILL":
        killed = True

    if killed:
        return stage_decision(
            "EXPENSIVE_ARTIFACTS", SKIP,
            "candidate clearly contradicted: the recorded challenge "
            "verdict (killed) is authoritative — engineering artifacts "
            "for a dead candidate are dead compute (directive §23: "
            "candidate rejected → no CAD, no visual package, no buyer "
            "PDF)",
            next_action="generate a competing mechanism (evolution) or "
                        "close the run honestly",
            skip_class=NOT_REQUIRED,
            evidence={"challenge_killed": True,
                      "attack_overall": attack.get("overall"),
                      "adjudication_verdict":
                          (adjudication.get("council") or {}).get(
                              "verdict")})

    if not mm.get("intervention"):
        return stage_decision(
            "EXPENSIVE_ARTIFACTS", SKIP,
            "no retained candidate: nothing to engineer",
            next_action="evolution layer or honest no-invention record",
            skip_class=NOT_REQUIRED,
            evidence={"intervention_recorded": False})

    # capability-insufficient synthesis → BLOCKED (infra class)
    from discovery_fabric.engine import stage_entry as _se
    cap = _se.synthesis_capability_state(
        _envelope_proxy(env_state))
    if cap.get("state") == "CAPABILITY_INSUFFICIENT":
        return stage_decision(
            "EXPENSIVE_ARTIFACTS", BLOCK,
            "synthesis capability insufficient — engineering compute on "
            "a degraded pseudo-invention is refused (R453-LEAN-CORE "
            "admission ground); this is an infrastructure class state, "
            "resumable, never a scientific rejection (Art. LXI)",
            next_action="restore transport capability and resume",
            skip_class=BLOCKED,
            evidence={"capability_state": cap})

    return stage_decision("EXPENSIVE_ARTIFACTS", RUN,
                          "candidate survived the recorded gauntlet — "
                          "escalate toward engineering representation "
                          "(directive §5)",
                          next_action="engineering specification → "
                                      "geometry → package")


class _envelope_proxy:
    """A read-only attribute shim so stage_entry helpers (typed for
    the Candidate dataclass) can read a plain dict envelope."""

    def __init__(self, d: Dict[str, Any]):
        self._d = d

    def __getattr__(self, name: str) -> Any:
        return self._d.get(name)


# ---------------------------------------------------------------------------
# Problem-build retrieval stopping (§14, the connector loop)
# ---------------------------------------------------------------------------

def retrieval_stopping(sources_done: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The connector-level stopping rule for the evidence-bound problem
    build: after each source completes, decide whether the REMAINING
    sources materially reduce uncertainty about the problem binding.

    Sources_done entries carry {source, role, status, count, relevant}.
    A source that returned >=1 RELEVANT record counts toward coverage
    of its role (failure / science). The build needs one usable
    failure-or-science anchor; once it has BOTH role anchors (or one
    anchor plus a second completed source), remaining connectors are
    SKIPPED_LOW_VALUE — recorded, never silently dropped."""
    ok = [s for s in sources_done
          if s.get("status") == "OK" and int(s.get("relevant") or 0) > 0]
    roles = {s.get("role") for s in ok}
    both_anchors = ("failure" in roles) and ("science" in roles)
    enough = both_anchors and len(ok) >= 2
    return {
        "stop": enough,
        "n_sources_completed": len(sources_done),
        "n_relevant_sources": len(ok),
        "roles_covered": sorted(r for r in roles if r),
        "decision_basis": ("both failure and science role anchors "
                           "retrieved with relevant records — additional "
                           "connectors would not materially change the "
                           "problem binding (directive §14)"
                           if enough else
                           "role coverage incomplete — continue "
                           "retrieval"),
        "skipped_would_be": [s.get("source") for s in sources_done
                             if s.get("status") != "OK"],
    }
