"""discovery_fabric/engine/problem_router.py — R178 DIR-3 SHIP: the
problem-class route split (the kill criterion made engine policy).

THE MEASURED BASIS (V138 / r177s1 DIR-3 record, all numbers recomputed
from the committed pair bytes of eval/r175s3_dir3/ + eval/r175_compute_
matched/): on MITIGATION problems (question_type
"intervention-proposal", the f31e shape) the multi-stage exploration
grid adds no measured value — genuine novel-candidate wins 1/12 (8.3%,
one contradiction win), departure 0/12, dominance ties 7/12 (the
pipeline emitted the baseline's own answer), plain best-of-N wins
2/12; the compute-matched non-loss (0.75 win+tie CI[0.428,0.945]) is
achieved by the best-of-N + critique + revise recipe itself at the
same 6-call budget. Per the reviewer's kill criterion (AM52/AM53):
ship best-of-N + verifier for mitigation; reserve the multi-stage
architecture where it must PROVE invention value (question_type
"novel-mechanism", the r176 shape — the AM53 gate is the standing
acceptance there).

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
  * the grid-disable set the EngineRun conductor consumes: mitigation
    problems run with the exploration grid DISABLED (typed
    SKIPPED_ROUTE_MITIGATION_CHEAP_ARM, persisted in the grid record
    with the measured basis) while ensemble + composer verifier stay
    on (the cheap arm); invention-shaped problems run the full
    architecture unchanged.

WHAT IT DOES NOT DO: no routing on domain keywords, no heuristics, no
prompt changes, no verifier weakening (the composer's deterministic
contract + constraint + consistency checks run on EVERY route — the
verifier is not a stage you can save cost on; the DIR-4 ablation tests
stages, not the verifier legs)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

ROUTER_VERSION = "problem_router/1.0.0"

#: question_type -> route. The two MEASURED classes are wired; any
#: other declared type conservatively routes to the ARCHITECTURE (the
#: full gauntlet) — unknown shapes never silently lose stages.
_KNOWN_ROUTES: Dict[str, str] = {
    # the mitigation-correctness shape (f31e): the kill criterion
    # measured the multi-stage grid at 8.3% genuine value-add — RETIRED
    # for this class; the cheap arm (ensemble best-of-N + composer
    # validate-repair verifier) serves it.
    "intervention-proposal": "CHEAP_ARM",
    # the invention shape (r176): the multi-stage architecture runs;
    # its standing acceptance is the AM53 genuine-novel-win gate.
    "novel-mechanism": "ARCHITECTURE",
}

#: the grid-disable set per route. CHEAP_ARM disables the exploration
#: grid (the multi-candidate multi-angle generator — the measured
#: no-op leg on mitigation); ARCHITECTURE disables nothing (the
#: conductor's own disabled_stages list still applies on top).
_GRID_DISABLE: Dict[str, List[str]] = {
    "CHEAP_ARM": ["EXPLORATION_GRID"],
    "ARCHITECTURE": [],
}

#: the measured basis string carried in every typed skip record (the
#: numbers are the r177s1 DIR-3 recompute from committed bytes; the
#: record cites the artifacts so the auditor can re-derive them).
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
    "invention-shaped problem (question_type novel-mechanism, the r176 "
    "corpus shape): the multi-stage architecture runs unchanged; its "
    "standing acceptance is the AM53 genuine-novel-candidate-win gate "
    "(>=50% genuine wins, dominance ties and plain best-of-N wins "
    "excluded, auditor-judged blind, CI lower >50% at n>=24)"
)

_UNKNOWN_BASIS = (
    "question_type missing or not in the measured route table — the "
    "conservative default is the FULL architecture (no stage is "
    "silently lost on an unclassified problem); classify the corpus "
    "item to take a measured route"
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
            "basis": (_MITIGATION_BASIS
                      if route == "CHEAP_ARM" else _ARCHITECTURE_BASIS),
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
        note = ("mitigation class: the exploration grid is disabled by "
                "the measured route (the cheap arm — ensemble best-of-N "
                "+ the composer validate-repair verifier — serves this "
                "class); every verifier leg stays on")
    elif not verdict["known"]:
        note = ("unclassified problem: full architecture (conservative "
                "default; nothing silently lost)")
    return {
        "disabled_stages": disabled,
        "route": verdict["route"],
        "problem_class": verdict["problem_class"],
        "known": verdict["known"],
        "basis": verdict["basis"],
        "router_version": ROUTER_VERSION,
        "note": note,
    }
