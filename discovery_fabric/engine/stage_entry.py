"""discovery_fabric/engine/stage_entry.py — R399 W2: the ONE shared
entry-justification helper.

Directive (R399, "ENTRY JUSTIFICATION — ONE SHARED HELPER ONLY"):
"Do not create a new governance subsystem. Implement one shared helper
used by stages to stamp entry_status / prerequisite /
prerequisite_evidence / skip_reason onto the existing stage envelope."

Every expensive stage must be able to answer:
    "Why was this stage allowed to consume compute?"

This module is exactly that helper plus its prerequisite table — nothing
else. It does not decide anything the conductor did not already decide;
it RECORDS the justification so a reader of the run record can audit why
compute was spent (or honestly not spent).

Vocabulary (directive examples):
    ALLOWED / VERIFIED_EVIDENCE
    ALLOWED / PHYSICS_ELIGIBLE
    ALLOWED / BASELINE_AVAILABLE
    SKIPPED / EVIDENCE_VERIFICATION_FAILED
    SKIPPED / UPSTREAM_TERMINAL_FAILURE

R453-LEAN-CORE (the external auditor mandate — subtraction, not
features) adds the ADAPTIVE ADMISSION rule through this SAME door (no
new framework): the expensive stages admit only when the run actually
has something for them to work on —
    SKIPPED / SYNTHESIS_CAPABILITY_INSUFFICIENT   SYNTHESIZE was served
        by a CHEAP_EMERGENCY_FALLBACK model on a STRONG request — a
        degraded synthesis is not an ok synthesis, and downstream
        compute would be ceremony on a pseudo-invention (Art. IV/XVIII)
    SKIPPED / NO_RETAINED_CANDIDATE                nothing survived the
        chain's own retention gates — there is nothing to attack, rank,
        or design experiments for (attack is skippable ONLY when there
        is nothing to attack; a verified primary candidate or a
        retained mechanism-space candidate both count as something)

Semantics:
    entry_status     ALLOWED | SKIPPED
    prerequisite     the condition that must hold for the stage to be
                     worth executing (e.g. UPSTREAM_COMPLETE,
                     VERIFIED_EVIDENCE, BASELINE_AVAILABLE)
    prerequisite_evidence  the measured values the decision rested on
                     (counts, stage names, error strings) — never a
                     narrative
    skip_reason      when SKIPPED: the honest machine reason

Epistemic contract (Art. XXV / XXI.3): a skip is a RECORDED refusal,
never an absence claim and never a silent code path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from discovery_fabric.engine.candidate import Candidate

ENTRY_HELPER_VERSION = "stage_entry/1.1.0"

#: R453-LEAN-CORE: the stages whose compute is admitted only when the
#: run has something for them to work on. ADJUDICATION and CLASSIFY are
#: deliberately NOT here — they are the run's terminal classifiers and
#: must stay reachable to record the honest UNKNOWN/INSUFFICIENT state
#: (the mandate's capability fail-closed contract).
ADAPTIVE_ADMISSION_STAGES = frozenset({
    "MECHANISM_SPACE", "MULTI_SOURCE_DISCOVERY", "COLLISION",
    "PHYSICS", "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT",
    "NEXT_BEST_ACTION", "RANK",
})

# Evidence classes that count as a VERIFIED_EVIDENCE_ITEM: an item the
# classification adjudicated as carrying mechanism support (R394 s5).
# BACKGROUND/ANALOGY/IRRELEVANT/CONTRADICTORY do NOT count — a topically
# relevant but mechanism-irrelevant item is exactly NOT a verified
# evidence item for candidate generation.
VERIFYING_CLASSES = ("DIRECT_SUPPORT", "PARTIAL_SUPPORT")


def verified_evidence_items(env: Candidate) -> List[Dict[str, Any]]:
    """The evidence items that passed claim-level verification
    (classification as mechanism-supporting) — the countable basis for
    the VERIFIED_EVIDENCE prerequisite (R399 W2.3)."""
    ec = env.evidence_classification or {}
    items = ec.get("items") if isinstance(ec, dict) else None
    if not isinstance(items, list):
        return []
    return [it for it in items
            if isinstance(it, dict)
            and it.get("classification") in VERIFYING_CLASSES]


def verified_evidence_prerequisite(env: Candidate) -> Dict[str, Any]:
    """The VERIFIED_EVIDENCE prerequisite record: satisfied + the
    measured counts it rests on (never a bare boolean)."""
    ev = env.adjudication or {}
    verification = ev.get("evidence_verification") or {}
    verified_items = verified_evidence_items(env)
    counts = (env.evidence_classification or {}).get("counts") or {}
    return {
        "prerequisite": "VERIFIED_EVIDENCE",
        "satisfied": bool(verified_items
                          or verification.get("verified")),
        "prerequisite_evidence": {
            "n_verified_evidence_items": len(verified_items),
            "n_direct_support": counts.get("DIRECT_SUPPORT", 0),
            "n_partial_support": counts.get("PARTIAL_SUPPORT", 0),
            "n_items_total": ((env.evidence_classification or {})
                              .get("n_items")
                              or len(env.evidence or [])),
            "span_binding_verified": bool(
                verification.get("verified")),
            "basis": (">=1 evidence item classified "
                      "DIRECT_SUPPORT/PARTIAL_SUPPORT, or the candidate's "
                      "span binding verified (R394 s5 classification + "
                      "a2/verify)"),
        },
    }


def synthesis_capability_state(env: Optional[Candidate]) -> Dict[str, Any]:
    """R453-LEAN-CORE: did SYNTHESIZE run at the REQUESTED capability?

    Reads the synthesis provenance the SynthesizeAdapter stamps onto
    the envelope (provenance.synthesis.task_degradation — the registry's
    own measured record of the call that actually served). A STRONG
    request served by CHEAP_EMERGENCY_FALLBACK is CAPABILITY_INSUFFICIENT
    — the mandate's fail-closed rule: degraded STRONG is a hard stop,
    never a cheap success. No record (legacy envelopes) is UNKNOWN —
    never silently treated as either blocked or fine (Art. XXV)."""
    if env is None:
        return {"state": "UNKNOWN", "basis": "no envelope"}
    syn = ((env.provenance or {}).get("synthesis") or {})
    deg = syn.get("task_degradation") or {}
    if not deg:
        return {"state": "UNKNOWN",
                "basis": "no task_degradation record on the synthesis "
                         "provenance (legacy envelope)"}
    degraded = (deg.get("task_capability_match") is False
                and str(deg.get("actual_task_capability")) ==
                "CHEAP_EMERGENCY_FALLBACK")
    return {
        "state": "CAPABILITY_INSUFFICIENT" if degraded else "OK",
        "requested_task": deg.get("requested_task"),
        "actual_task_capability": deg.get("actual_task_capability"),
        "serving_model": syn.get("model"),
        "serving_provider": syn.get("provider"),
        "basis": ("the registry's own task-degradation record for the "
                  "call that served SYNTHESIZE (R451-C1.4) — a STRONG "
                  "stage served by CHEAP_EMERGENCY_FALLBACK is not an "
                  "ok synthesis"),
    }


def retained_candidate_facts(env: Optional[Candidate]) -> Dict[str, Any]:
    """R453-LEAN-CORE: the measured retention facts — is there anything
    for the expensive stages to work on?

    A retained candidate exists iff the mechanism space retained >= 1
    candidate OR the primary synthesized candidate's evidence
    verification passed (a verified primary is something to attack; a
    mechanism-space candidate is something to rank). Both counts are
    recorded — never a bare boolean."""
    if env is None:
        return {"retained": False, "n_ms_retained": 0,
                "primary_verified": False, "basis": "no envelope"}
    ms = env.mechanism_space or {}
    ms_retained = int(ms.get("n_candidates_retained") or 0)
    verified = bool(((env.adjudication or {})
                     .get("evidence_verification") or {})
                    .get("verified", False))
    return {
        "n_ms_retained": ms_retained,
        "primary_verified": verified,
        "retained": bool(ms_retained or verified),
        "ms_state": ms.get("state"),
        "basis": ("mechanism-space retained candidates OR the primary "
                  "candidate's evidence verification — either is "
                  "something to attack/rank; neither is a fabrication"),
    }


def justify(stage: str,
            env: Optional[Candidate],
            failed_stages: Optional[Dict[str, str]] = None,
            skipped_stages: Optional[Set[str]] = None) -> Dict[str, Any]:
    """WHY was this stage allowed to consume compute? The one shared
    helper (R399). Returns the entry block stamped onto the stage's
    envelope entry.

    Rule set (small, explicit, per directive):
      1. UPSTREAM_TERMINAL_FAILURE — a stage whose blocker (per
         DOWNSTREAM_BLOCKERS) FAILED or was itself SKIPPED (the R399
         skip cascade: a skipped stage is as dead as a failed one for
         everything downstream of it) is SKIPPED with the blocking
         stage + its recorded reason.
      2. VERIFIED_EVIDENCE — the expensive candidate-generation stages
         (the diversity grid, the ensemble) require >= 1 verified
         evidence item (R399 W2.3). With zero verified items the stage
         is SKIPPED / EVIDENCE_VERIFICATION_FAILED.
      3. Otherwise ALLOWED, with the prerequisite that held.

    The helper never raises and never mutates the envelope: it is a
    recorder, not a gate (the conductor applies its verdict)."""
    out: Dict[str, Any] = {"entry_helper_version": ENTRY_HELPER_VERSION,
                           "stage": stage}
    failed = failed_stages or {}
    skipped = set(skipped_stages or set())
    # 1. upstream terminal failure (failure OR skip cascade)
    from discovery_fabric.engine.run import DOWNSTREAM_BLOCKERS  # noqa: PLC0415 — one authority
    blockers = {b for b, blocked in DOWNSTREAM_BLOCKERS.items()
                if stage in blocked}
    for blocker in sorted(blockers):
        if blocker in failed:
            out.update({
                "entry_status": "SKIPPED",
                "prerequisite": "UPSTREAM_COMPLETE",
                "skip_reason": (f"UPSTREAM_TERMINAL_FAILURE: stage "
                                f"{blocker} failed: "
                                f"{str(failed[blocker])[:200]}"),
                "prerequisite_evidence": {"failed_stage": blocker},
            })
            return out
        if blocker in skipped:
            out.update({
                "entry_status": "SKIPPED",
                "prerequisite": "UPSTREAM_COMPLETE",
                "skip_reason": (f"UPSTREAM_TERMINAL_FAILURE: stage "
                                f"{blocker} was skipped upstream "
                                f"(SKIPPED_UPSTREAM_FAILURE) — everything "
                                f"downstream of a skipped stage is dead "
                                f"compute (R399 W2.5)"),
                "prerequisite_evidence": {"skipped_stage": blocker},
            })
            return out
    # 1b. R453-LEAN-CORE adaptive admission — the expensive stages are
    #     admitted only when the run has something for them to work on:
    #     (i)  SYNTHESIZE must have run at the requested capability (a
    #          CHEAP_EMERGENCY_FALLBACK synthesis is not an ok synthesis);
    #     (ii) a retained candidate must exist for the stages that
    #          consume one (MECHANISM_SPACE itself only needs the
    #          synthesized primary + verified evidence — it CREATES the
    #          retained set). ADJUDICATION/CLASSIFY never hit this rule
    #          (terminal classifiers; the honest UNKNOWN state must stay
    #          reachable).
    if stage in ADAPTIVE_ADMISSION_STAGES and env is not None:
        cap = synthesis_capability_state(env)
        if cap["state"] == "CAPABILITY_INSUFFICIENT":
            out.update({
                "entry_status": "SKIPPED",
                "prerequisite": "SYNTHESIS_AT_REQUESTED_CAPABILITY",
                "skip_reason": (
                    "SYNTHESIS_CAPABILITY_INSUFFICIENT: the synthesis "
                    "call was served by a CHEAP_EMERGENCY_FALLBACK model "
                    "on a STRONG request — a degraded synthesis is not "
                    "an ok synthesis, and this stage's compute would be "
                    "ceremony on a pseudo-invention (R453-LEAN-CORE "
                    "fail-closed; Art. IV/XVIII)"),
                "prerequisite_evidence": cap,
            })
            return out
        if stage != "MECHANISM_SPACE":
            facts = retained_candidate_facts(env)
            if not facts["retained"]:
                out.update({
                    "entry_status": "SKIPPED",
                    "prerequisite": "RETAINED_CANDIDATE",
                    "skip_reason": (
                        "NO_RETAINED_CANDIDATE: zero mechanism-space "
                        "candidates retained and the primary candidate's "
                        "evidence verification did not pass — there is "
                        "nothing to attack, rank, or design experiments "
                        "for (R453-LEAN-CORE; attack is skippable only "
                        "when there is nothing to attack)"),
                    "prerequisite_evidence": facts,
                })
                return out
    # 2. verified-evidence prerequisite for expensive candidate
    #    generation (the grid / ensemble / mechanism-space sites call
    #    this helper with their stage names; the conductor's core stages
    #    have no evidence prerequisite — the chain already gates them)
    #    R401: MECHANISM_SPACE joins the expensive set — it generates
    #    candidates through five LLM instantiation calls.
    if stage in ("EXPLORATION_GRID", "ENSEMBLE", "MECHANISM_SPACE") \
            and env is not None:
        prereq = verified_evidence_prerequisite(env)
        if not prereq["satisfied"]:
            out.update({
                "entry_status": "SKIPPED",
                "prerequisite": prereq["prerequisite"],
                "skip_reason": ("EVIDENCE_VERIFICATION_FAILED: zero "
                                "verified evidence items on the envelope "
                                "— expensive candidate generation would "
                                "build candidates on unverified evidence "
                                "(R399 W2.3)"),
                "prerequisite_evidence":
                    prereq["prerequisite_evidence"],
            })
            return out
        out.update({
            "entry_status": "ALLOWED",
            "prerequisite": prereq["prerequisite"],
            "prerequisite_evidence": prereq["prerequisite_evidence"],
        })
        return out
    # 3. allowed — the default prerequisite is simply that no blocker
    #    fired (the chain's own ordering)
    out.update({
        "entry_status": "ALLOWED",
        "prerequisite": "UPSTREAM_COMPLETE",
        "prerequisite_evidence": {
            "failed_stages": sorted(failed.keys()),
            "skipped_stages": sorted(skipped)},
    })
    return out
