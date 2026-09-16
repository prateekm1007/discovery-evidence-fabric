"""discovery_fabric/engine/cheap_screen.py — R401B B8 + A4: the
CHEAP-FIRST SCIENTIFIC FILTER and the cost-aware stage model.

Directive order (B8):

  STRUCTURED MECHANISM
    -> MATERIAL DISTINCTNESS          (mechanism_space, already applied)
    -> REPRESENTABILITY               (cheap: domain detection)
    -> CHEAP PHYSICS / CONSTRAINT SCREEN  (cheap: declared-envelope
       bounds, no solver run)
    -> BASELINE SCREEN                (cheap: direction-of-effect)
    -> TOP-N                          (cheap score ranking)
    -> EXPENSIVE EVALUATION           (spec build + physics gate)
    -> ATTACK                         (deterministic + independent)
    -> IMPROVEMENT                    (existing repair loop)
    -> CAD / RELEASE                  (existing pipeline)

Rules that make this constitutional:
  - Skipped stages record explicit reasons (never silence).
  - Information is never skipped merely because the candidate is
    LIKELY to fail: the screen kills on CHEAPLY DECIDABLE defects only
    (representability of the mechanism class, declared-envelope
    impossibility, no predicted change vs baseline). Every screened
    candidate's full structured record is preserved — LEARNING-
    CRITICAL information stays available.
  - No UNKNOWN becomes an affirmative: an undecidable screen check is
    recorded UNDECIDED and the candidate ADVANCES (fail-open only in
    the direction of MORE evaluation, never less — the inverse of
    Art. IV's fail-closed, because this gate spends money, it does
    not admit claims).

A4 cost classes (the auto-generated stage model, not hand-maintained):
  CHEAP_DETERMINISTIC   local, deterministic, no LLM
  CHEAP_LLM             one bounded LLM call
  EXPENSIVE_LLM         multi-call LLM candidate generation
  EXPENSIVE_EVALUATION  full engineering evaluation / attack / package
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

CHEAP_SCREEN_VERSION = "cheap_screen/1.0.0"

# A4: the stage cost model — GENERATED from the adapter metadata +
# DOWNSTREAM_BLOCKERS (scripts/r401_stage_table.py emits the JSON
# artifact; this table is the executable copy the gauntlet reads).
# Sources: adapters.needs_network (network = LLM/search), capability
# class, DOWNSTREAM_BLOCKERS (consumers). Not hand-maintained prose.
STAGE_COST_CLASSES: Dict[str, str] = {
    "RETRIEVE": "CHEAP_LLM",
    "FREEZE": "CHEAP_DETERMINISTIC",
    "PREMISE_GATE": "CHEAP_DETERMINISTIC",
    "SYNTHESIZE": "CHEAP_LLM",
    "VERIFY": "CHEAP_DETERMINISTIC",
    "MECHANISM_SPACE": "EXPENSIVE_LLM",
    "MULTI_SOURCE_DISCOVERY": "CHEAP_LLM",
    "COLLISION": "CHEAP_LLM",
    "PHYSICS": "CHEAP_DETERMINISTIC",
    "ATTACK": "CHEAP_DETERMINISTIC",
    "CONTRADICTION": "CHEAP_DETERMINISTIC",
    "KILLER_EXPERIMENT": "CHEAP_DETERMINISTIC",
    # R481: the IMPROVE stage — one bounded LLM mutation per dead
    # candidate plus the child's gauntlet re-run (spec + attack +
    # independent attack + quality): the EXPENSIVE_LLM class, and the
    # stage is admission-gated like the other expensive stages (it
    # runs ONLY when kill evidence exists — the NO_KILL_EVIDENCE skip
    # is the R453 admission discipline applied to the loop closure)
    "IMPROVE": "EXPENSIVE_LLM",
    "ADJUDICATION": "CHEAP_DETERMINISTIC",
    "CLASSIFY": "CHEAP_DETERMINISTIC",
    "NEXT_BEST_ACTION": "CHEAP_DETERMINISTIC",
    "RANK": "CHEAP_DETERMINISTIC",
    "GAUNTLET_SPEC": "EXPENSIVE_EVALUATION",
    "GAUNTLET_PHYSICS_GATE": "CHEAP_DETERMINISTIC",
    "GAUNTLET_INDEPENDENT_ATTACK": "CHEAP_LLM",
    "GAUNTLET_PACKAGE": "EXPENSIVE_EVALUATION",
}

# domains the V0 hydraulic solver can represent (physics scope —
# Phase 7: no new solvers; out-of-scope = MECHANISM_NOT_SIMULATABLE,
# which ADVANCES with the honest disclosure, never a cheap kill)
_PHYSICS_REPRESENTABLE = {"fluidics_hydraulic", "medical_fluidics"}

# impossible declared envelopes (the cheap constraint screen — the same
# bound classes the physics gate enforces AFTER spec build; here they
# kill BEFORE the expensive evaluation when the CANDIDATE ITSELF
# declares the impossibility)
_IMPOSSIBLE_DECLARED = (
    re.compile(r"negative\s+(lumen|diameter|pressure|flow)", re.I),
    re.compile(r"\bdiameter\s*[:<>=-]+\s*0\s*(mm|micron|um)\b", re.I),
    re.compile(r"\bflow\s*[:<>=-]+\s*0\b", re.I),
    re.compile(r"perpetual|infinite\s+(flow|pressure|energy)", re.I),
    re.compile(r"\btemperature\s*(above|>|over)\s*500", re.I),
)

# direction-of-effect vocabulary (the baseline screen): the predicted
# effect must imply a CHANGE against the un-invented baseline
_DIRECTION_RE = re.compile(
    r"reduce|reduced|increase|increased|decrease|decreased|improve|"
    r"improved|extend|extended|slow|slower|faster|higher|lower|"
    r"prevent|prevented|delay|delayed|eliminate|survive|maintain|"
    r"preserve|beat|exceed|greater|less|fewer|more|fold|percent|%",
    re.I)


def screen_candidate(candidate: Dict[str, Any],
                     problem: Dict[str, Any]) -> Dict[str, Any]:
    """The cheap-first screen for ONE mechanism-space candidate.

    Checks (each records a verdict + basis; UNDECIDED advances):
      representability     mechanism-class domain detection (for the
                           honest MECHANISM_NOT_SIMULATABLE path — NOT
                           a kill; out-of-scope advances with the
                           disclosure)
      constraint_screen    declared-envelope impossibility (a KILL:
                           the candidate's own constraint set states a
                           physical impossibility)
      baseline_screen      direction-of-effect (a KILL only when the
                           predicted effect provably implies NO change
                           vs the baseline — explicitly "unchanged" or
                           equivalent wording; absent direction is
                           UNDECIDED and advances)

    Returns {state: ADVANCE | SCREENED_OUT, reasons[], cheap_score,
    checks{}} — the full basis travels with the record.
    """
    checks: Dict[str, Dict[str, Any]] = {}
    reasons: List[str] = []
    mech_text = str(candidate.get("mechanism") or "")
    pred_text = str(candidate.get("predicted_effect") or "")
    pred_full = pred_text + " " + str(
        candidate.get("testable_prediction") or "")
    constraint_text = " ".join(str(v) for v in (
        (candidate.get("constraint_set") or {}).get(
            "problem_constraint"),
        (candidate.get("constraint_set") or {}).get(
            "boundary_conditions"),
        (candidate.get("constraint_set") or {}).get(
            "stated_constraints")) if v)

    # 1. representability (advances either way — disclosure, not kill)
    from .domains import detect_domain
    dom = detect_domain(
        mech_text + " " + str(candidate.get("intervention") or "")) \
        .get("domain", "UNKNOWN")
    representable = dom in _PHYSICS_REPRESENTABLE
    checks["representability"] = {
        "verdict": "REPRESENTABLE" if representable
        else "MECHANISM_NOT_SIMULATABLE_EXPECTED",
        "detected_domain": dom,
        "basis": ("V0 hydraulic solver scope; out-of-scope mechanisms "
                  "ADVANCE with the honest MECHANISM_NOT_SIMULATABLE "
                  "disclosure (Phase 7: no fabricated physics)")}

    # 2. cheap constraint screen (kill only on declared impossibility)
    impossible_hits = [p.pattern for p in _IMPOSSIBLE_DECLARED
                       if p.search(constraint_text)]
    checks["constraint_screen"] = {
        "verdict": ("IMPOSSIBLE_DECLARED" if impossible_hits
                    else "NO_DECLARED_IMPOSSIBILITY"),
        "matched_patterns": impossible_hits,
        "basis": ("the candidate's OWN declared envelope matches an "
                  "impossibility class (negative lumen, zero flow, "
                  "perpetual motion, >500 K water-class thermal bound) "
                  "— the same bound families the physics gate enforces "
                  "after spec build, applied BEFORE the expensive "
                  "evaluation on declared values only")}
    if impossible_hits:
        reasons.append(
            "CONSTRAINT_SCREEN_IMPOSSIBLE_DECLARED: "
            + "; ".join(impossible_hits[:3]))

    # 3. baseline screen (kill only on provable no-change)
    if not pred_text.strip():
        checks["baseline_screen"] = {
            "verdict": "UNDECIDED",
            "basis": "no predicted effect text — cannot cheaply decide"}
    elif re.search(r"\b(unchanged|no change|remains? the same|"
                   r"equivalent to (the )?baseline|same as "
                   r"(the )?baseline)\b", pred_full, re.I):
        checks["baseline_screen"] = {
            "verdict": "NO_CHANGE_VS_BASELINE",
            "basis": ("the predicted effect explicitly states the "
                      "quantity is unchanged/equivalent to the "
                      "baseline — a baseline-equivalent candidate is "
                      "not an invention (killed early, Art. V-safe: "
                      "the same verdict the physics stage would "
                      "reach after the expensive evaluation)")}
        reasons.append(
            "BASELINE_SCREEN_NO_CHANGE: predicted effect explicitly "
            "equals the baseline")
    elif not _DIRECTION_RE.search(pred_full):
        checks["baseline_screen"] = {
            "verdict": "UNDECIDED",
            "basis": ("predicted effect carries no direction vocabulary "
                      "— undecidable cheaply; ADVANCES (never skipped "
                      "merely because it looks weak)")}
    else:
        checks["baseline_screen"] = {
            "verdict": "DIRECTION_OF_EFFECT_PRESENT",
            "basis": _DIRECTION_RE.search(pred_full).group(0)}

    # cheap score (for TOP-N ordering only — never a gate):
    #   representable +1 (cheaper downstream), bound mechanism support
    #   +2 (SUPPORTED) / +1 (PARTIAL), testable prediction +1,
    #   distinct operator provenance +1 — recorded, not tuned
    support = (candidate.get("mechanism_support") or {}).get(
        "mechanism_support_state")
    cheap_score = (
        (1 if representable else 0)
        + (2 if support == "SUPPORTED" else
           1 if support == "PARTIALLY_SUPPORTED" else 0)
        + (1 if (candidate.get("testable_prediction_check") or {})
           .get("testable") else 0)
        + (1 if candidate.get("derivation_trace") else 0))
    state = "SCREENED_OUT" if reasons else "ADVANCE"
    return {
        "cheap_screen_version": CHEAP_SCREEN_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "state": state,
        "reasons": reasons,
        "checks": checks,
        "cheap_score": cheap_score,
        "cheap_score_basis": ("ordering only — representable +1, "
                              "mechanism support +2/+1, testable "
                              "prediction +1, derivation trace +1; "
                              "NEVER a kill decision"),
        "policy": ("kills only on cheaply DECIDABLE defects (declared "
                   "impossibility, explicit baseline equivalence); "
                   "UNDECIDED advances; out-of-scope physics advances "
                   "with disclosure; every screened candidate's full "
                   "structured record is preserved (learning-critical "
                   "information)"),
    }


def rank_top_n(screened: List[Dict[str, Any]], top_n: int
               ) -> Dict[str, Any]:
    """TOP-N selection over ADVANCE candidates by cheap score.
    Deterministic tie-break: candidate_id. Candidates beyond the cap
    are recorded SKIPPED_TOPN with their rank + score (explicit reason,
    full record preserved)."""
    advancing = [s for s in screened if s["state"] == "ADVANCE"]
    order = sorted(advancing,
                   key=lambda s: (-s["cheap_score"],
                                  s.get("candidate_id") or ""))
    selected = order[:max(0, top_n)]
    deferred = order[max(0, top_n):]
    return {
        "n_advance": len(advancing),
        "top_n": top_n,
        "selected_ids": [s.get("candidate_id") for s in selected],
        "deferred": [{
            "candidate_id": s.get("candidate_id"),
            "rank": i + 1 + top_n,
            "cheap_score": s["cheap_score"],
            "skip_reason": ("SKIPPED_TOPN: cheap-score rank beyond the "
                            "top-N evaluation budget — the candidate "
                            "ADVANCED the screens and is preserved in "
                            "full for future evaluation windows"),
        } for i, s in enumerate(deferred)],
        "ranking_rule": ("cheap_score desc, candidate_id asc — "
                         "deterministic; deferred candidates are NOT "
                         "rejected, only deferred"),
    }
