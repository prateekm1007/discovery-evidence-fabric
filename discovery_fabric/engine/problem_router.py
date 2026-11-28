"""discovery_fabric/engine/problem_router.py — R183 KILL SHIP: every
problem class routes to the cheap arm (the kill criterion made engine
policy for invention as well as mitigation). Supersedes the R178
problem-class route split (problem_router/1.0.0); the byte-derived
basis is eval/r183_kill_decision.json.

THE MEASURED BASIS (V138 / r177s1 DIR-3 record, all numbers recomputed
from the committed pair bytes of eval/r175s3_dir3/ + eval/r175_compute_
matched/): on MITIGATION problems (question_type
"intervention-proposal", the f31e shape) the multi-stage exploration
grid adds no measured value — genuine novel-candidate wins 1/12 (8.3%,
one contradiction win), departure 0/12, dominance ties 7/12 (the
pipeline emitted the baseline's own answer), plain best-of-N wins
2/12; the compute-matched non-loss (0.75 win+tie CI[0.428,0.945]) is
achieved by the best-of-N + critique + revise recipe itself at the
same 6-call budget. THE R183 KILL EXTENDS THIS TO THE INVENTION CLASS
(eval/r183_kill_decision.json, independent recompute
eval/r183_collider_run/tally.json): genuine 4/12 (33.3%, Wilson CI lower
0.138), paired collider delta 0.0, 0 collision champions; from 4 wins
at n=12 even 12/12 remaining gives 16/24 < 17, so the >=17/24 gate is
mathematically unreachable. Both measured classes now ship best-of-N +
critique + revise + verifier.

WHAT THIS MODULE DOES (deterministic, zero LLM):
  * classify(problem) -> a typed ROUTE verdict from the problem's own
    declared question_type — the author's classification is AUTHORITY
    (never re-derived or second-guessed here; a wrong class is fixed
    at the corpus, not silently re-routed);
  * route_for_problem(problem) -> {"route": "CHEAP_ARM"|"ARCHITECTURE",
    "problem_class": ..., "basis": ...} with a typed fallback for
    unknown/missing question_type (ARCHITECTURE — the conservative
    default: the multi-stage path is the one that must justify itself,
    so unknown shapes keep the full gauntlet, never silently lose it);
  * the grid-disable set the EngineRun conductor consumes: BOTH measured
    problem classes run with the exploration grid DISABLED (typed
    SKIPPED_ROUTE_MITIGATION_CHEAP_ARM — the historical label is kept for
    byte compatibility — persisted in the grid record with the measured
    basis) while ensemble + composer verifier stay on (the cheap arm);
    unclassified packets keep the conservative full-architecture
    fallback until they are classified.

WHAT IT DOES NOT DO: no routing on domain keywords, no heuristics, no
prompt changes, no verifier weakening (the composer's deterministic
contract + constraint + consistency checks run on EVERY route — the
verifier is not a stage you can save cost on; the DIR-4 ablation tests
stages, not the verifier legs)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

ROUTER_VERSION = "problem_router/2.0.0"

#: question_type -> route. BOTH measured classes are now CHEAP_ARM:
#: mitigation was retired at 1/12 genuine (8.3%, r177s1) and the
#: invention class at 4/12 genuine (33.3%, CI lower 0.138, paired
#: collider delta 0.0, 0 collision champions — eval/r183_kill_decision.json,
#: independently recomputed in eval/r183_collider_run/tally.json).
#: The >=17/24 gate was mathematically unreachable from the landed
#: bytes (4 + 12 remaining = 16 < 17). An UNCLASSIFIED packet keeps the
#: conservative full-architecture fallback until it is classified;
#: the verifier still runs on every problem (never a cost lever).
_KNOWN_ROUTES: Dict[str, str] = {
    "intervention-proposal": "CHEAP_ARM",
    "novel-mechanism": "CHEAP_ARM",
}

#: the grid-disable set per route. CHEAP_ARM disables the exploration
#: grid (the multi-candidate multi-angle generator — the measured
#: no-op leg on BOTH problem classes); ARCHITECTURE is retained only
#: as a typed legacy value (no problem class routes to it now; the
#: conductor's own disabled_stages list still applies on top).
_GRID_DISABLE: Dict[str, List[str]] = {
    "CHEAP_ARM": ["EXPLORATION_GRID"],
    "ARCHITECTURE": [],
}

#: the byte-derived basis carried in every typed skip record. Two
#: independent recomputes, one per problem class, both from committed
#: pair bytes; the auditor can re-derive from the cited artifacts.
_MITIGATION_BASIS = (
    "DIR-3 kill criterion (r177s1 eval/r177s1_dir3_keep_retire.json, "
    "V138): on mitigation problems the multi-stage exploration grid "
    "measured genuine novel-candidate wins 1/12 (8.3%), departure "
    "0/12, dominance ties 7/12, plain best-of-N wins 2/12 "
    "(eval/r175s3_dir3/ pair bytes); the compute-matched non-loss "
    "0.75 CI[0.428,0.945] is the best-of-N+critique+revise+verifier "
    "recipe's own at the same 6-call budget "
    "(eval/r175_compute_matched/SUMMARY.json) — the grid is RETIRED "
    "for this problem class and the cheap arm serves it"
)

_ARCHITECTURE_BASIS = (
    "R183 KILL (eval/r183_kill_decision.json, independent recompute "
    "eval/r183_collider_run/tally.json): the invention class is RETIRED "
    "too — genuine novel-candidate wins 4/12 (33.3%, Wilson CI "
    "[0.138,0.609]), paired collider delta 0.0, 0 collision champions, "
    "dominance ties 4/12 and plain best-of-N wins 4/12 excluded per "
    "AM53; from 4 wins at n=12 even 12/12 remaining gives 16/24 < 17, "
    "so the >=17/24 score-4 gate is mathematically unreachable. Ship "
    "best-of-N + critique + revise + verifier for every problem class."
)

_UNKNOWN_BASIS = (
    "question_type missing or not in the measured route table — after "
    "the R183 kill decision BOTH measured classes (mitigation + "
    "invention) route to the cheap arm; an unclassified packet keeps the "
    "conservative FULL-architecture fallback (no stage is silently lost "
    "before it is classified); classify the item to take the cheap arm"
)


def classify(problem: Dict[str, Any]) -> str:
    """Return the problem's declared class label (the author's
    question_type verbatim, lowercased; '' when absent). The declared
    type is authority — this function never re-derives it."""
    return str((problem or {}).get("question_type") or "").strip().lower()


def route_for_problem(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Typed route verdict for one problem packet. Deterministic, zero
    LLM. Returns {"route", "problem_class", "known", "basis",
    "router_version"}."""
    qtype = classify(problem)
    if qtype in _KNOWN_ROUTES:
        route = _KNOWN_ROUTES[qtype]
        return {
            "route": route,
            "problem_class": qtype,
            "known": True,
            "basis": (_MITIGATION_BASIS if qtype == "intervention-proposal"
                      else _ARCHITECTURE_BASIS),
            "router_version": ROUTER_VERSION,
        }
    return {
        "route": "ARCHITECTURE",
        "problem_class": qtype or "<unclassified>",
        "known": False,
        "basis": _UNKNOWN_BASIS,
        "router_version": ROUTER_VERSION,
    }


def route_disabled_stages(problem: Dict[str, Any],
                          extra: Optional[List[str]] = None
                          ) -> Dict[str, Any]:
    """The conductor-facing decision: the effective disabled-stages set
    for a problem = (the route's grid-disable set) UNION (the caller's
    explicit disabled_stages). Returns {"disabled_stages", "route",
    "problem_class", "known", "basis", "router_version", "note"} — the
    conductor persists this into the run record (Art. XXV: a skip is a
    recorded refusal, never absence)."""
    verdict = route_for_problem(problem)
    disabled: List[str] = []
    for stage in _GRID_DISABLE.get(verdict["route"], []):
        if stage not in disabled:
            disabled.append(stage)
    for stage in (extra or []):
        if stage not in disabled:
            disabled.append(stage)
    note = ""
    if verdict["route"] == "CHEAP_ARM":
        note = ("kill criterion: the exploration grid is disabled on "
                "every problem class (the cheap arm — ensemble best-of-N "
                "+ the composer validate-repair verifier — serves this "
                "class); every verifier leg stays on")
    elif not verdict["known"]:
        note = ("unclassified problem: full architecture (conservative "
                "fallback; both measured classes route to the cheap "
                "arm; classify the item to take that route)")
    return {
        "disabled_stages": disabled,
        "route": verdict["route"],
        "problem_class": verdict["problem_class"],
        "known": verdict["known"],
        "basis": verdict["basis"],
        "router_version": ROUTER_VERSION,
        "note": note,
    }
