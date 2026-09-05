"""discovery_fabric/r411/collision.py — Directive s8: candidate collision
and deduplication before admission.

Three collision surfaces, all REQUIRED before a candidate can be admitted
to the scored pool:
  1. MECHANISM_CEMETERY (110 chained entries, orchestrator authority):
     check_candidate_against_cemetery + typed distinction required for
     any hit (Art. LI: the cemetery is READ by the generator — this is
     the mechanism that makes prior failure knowledge change this
     campaign's search).
  2. EXISTING PORTFOLIO: the four lead packages + P14 core mechanisms.
     Portfolio biases are NOT discovery seeds (directive s21), but they
     ARE collision targets (s8): a candidate that re-creates an existing
     package's mechanism is NO_MEANINGFUL_DISTINCTION (unless the typed
     distinction survives).
  3. INTRA-CAMPAIGN: mechanism_space.compare_candidates — the repo's
     distinctness instrument with EQUIVALENT/DISTINCT/INDETERMINATE
     verdicts (Art. XLII: the generator is not the distinctness
     authority; here the instrument is structural, independent of the
     generating LLM's wording choices).

Typed distinction vocabulary (directive s8): NEW_MECHANISM,
NEW_CAUSAL_CONFIGURATION, NEW_IMPLEMENTATION, NEW_CONTROL_STRATEGY,
NEW_MATERIAL_CONFIGURATION, NEW_MEASUREMENT_METHOD, NEW_APPLICATION,
NO_MEANINGFUL_DISTINCTION.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from discovery_fabric.engine.mechanism_space import compare_candidates

COLLISION_VERSION = "R411-COLLISION-V1"

TYPED_DISTINCTIONS = [
    "NEW_MECHANISM", "NEW_CAUSAL_CONFIGURATION", "NEW_IMPLEMENTATION",
    "NEW_CONTROL_STRATEGY", "NEW_MATERIAL_CONFIGURATION",
    "NEW_MEASUREMENT_METHOD", "NEW_APPLICATION",
    "NO_MEANINGFUL_DISTINCTION",
]

# The existing portfolio's core mechanisms as COLLISION TARGETS ONLY
# (directive s21: not seeds — the campaign never reads these for
# generation; they exist here so a discovered candidate cannot silently
# duplicate an existing package).
PORTFOLIO_MECHANISMS = [
    {
        "package": "P04",
        "mechanism_text": (
            "passive drainage priority safety floor: a passive hydraulic "
            "resistance network that preferentially drains through a "
            "low-resistance path when pressure exceeds a threshold, "
            "avoiding overdrainage in a shunt-like flow system"),
    },
    {
        "package": "P08",
        "mechanism_text": (
            "near-infrared photovoltaic power delivery: NIR light "
            "illuminating photovoltaic cells through tissue to power an "
            "implanted device, replacing percutaneous leads and "
            "transcutaneous energy transfer coils"),
    },
    {
        "package": "P11",
        "mechanism_text": (
            "gravity compensation hydraulic damper: a fluid damper whose "
            "damping rate adapts to posture-induced pressure transients "
            "by gravity-driven valve positioning, attenuating flow "
            "transients in a passive hydraulic circuit"),
    },
    {
        "package": "P13",
        "mechanism_text": (
            "self-referencing piezoresistive pressure sensor: dual "
            "matched sensing elements sharing a common-mode drift "
            "component, subtracted to reject common-mode drift and "
            "temperature error"),
    },
    {
        "package": "P14",
        "mechanism_text": (
            "acoustic obstruction detection: acoustic transmission "
            "measurement across a fluid path to detect partial "
            "obstruction from signal attenuation changes"),
    },
]

_DISTINCTION_RULES = [
    # (marker terms in the candidate's own novelty surface, typed class)
    (["new physical effect", "different physical phenomenon",
      "different effect class", "novel mechanism"], "NEW_MECHANISM"),
    (["reconfigur", "different causal order", "new topology",
      "new configuration", "rearranged"], "NEW_CAUSAL_CONFIGURATION"),
    (["implementation", "engineering realization", "different embodiment"],
     "NEW_IMPLEMENTATION"),
    (["control strategy", "feedback law", "controller", "control policy"],
     "NEW_CONTROL_STRATEGY"),
    (["material configuration", "material system", "coating system",
      "material substitution"], "NEW_MATERIAL_CONFIGURATION"),
    (["measurement method", "sensing method", "detection method",
      "measurement channel"], "NEW_MEASUREMENT_METHOD"),
    (["new application", "different application", "retarget",
      "cross-domain transfer"], "NEW_APPLICATION"),
]


def _portfolio_overlap(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Term-overlap screen against the portfolio mechanisms (deterministic
    token intersection; a hit goes to the typed-distinction test, never
    straight to rejection — an implementation difference can still be a
    commercially valuable typed distinction, honestly labeled).
    A mechanism-level overlap requires >=2 shared CORE terms, or ONE
    SPECIFIC term (generic vocabulary like 'flow'/'pressure' alone is
    incidental, not mechanism-level)."""
    text = " ".join(str(candidate.get(k) or "") for k in
                    ("technology_name", "problem", "causal_chain",
                     "intervention", "unexploited_phenomenon",
                     "predicted_effect")).lower()
    words = set(re.findall(r"[a-z]{4,}", text))
    # generic core terms appear across engineering domains; specific
    # terms identify a package mechanism almost uniquely
    generic_core = {"pressure", "hydraulic", "flow", "sensor",
                    "resistance", "valve", "drift"}
    specific_core = {"drainage", "damper", "acoustic", "attenuation",
                     "photovoltaic", "infrared", "subtraction",
                     "common-mode", "obstruction"}
    hits = []
    for pm in PORTFOLIO_MECHANISMS:
        pw = set(re.findall(r"[a-z]{4,}", pm["mechanism_text"]))
        inter = words & pw
        shared_generic = inter & generic_core
        shared_specific = inter & specific_core
        if len(shared_specific) >= 1 or len(shared_generic) >= 2:
            hits.append({
                "package": pm["package"],
                "shared_core_terms": sorted(shared_specific |
                                            shared_generic),
            })
    return hits


def check_cemetery(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Art. LI: the generator READS the cemetery. The repo's own gate:
    PROVEN_INVARIANT violations hard-block (physics proven impossible);
    STRONG_CONSTRAINT violations warn (require typed distinction);
    other lessons are informational and travel with the candidate."""
    from orchestrator.mechanism_cemetery import \
        check_candidate_against_cemetery
    text = " ".join(str(candidate.get(k) or "") for k in
                    ("technology_name", "problem", "causal_chain",
                     "intervention", "unexploited_phenomenon"))
    try:
        result = check_candidate_against_cemetery(text)
    except Exception as e:  # cemetery load failure is infrastructure, not
        # scientific rejection (Art. LXI)
        return {
            "status": "CEMETERY_CHECK_INFRASTRUCTURE_FAILURE",
            "error": str(e)[:200],
        }
    return {
        "status": "OK",
        "cemetery_verdict": result.get("verdict"),
        "hard_blocks": result.get("hard_blocks", []),
        "warnings": result.get("warnings", []),
        "informational_count": len(result.get("informational", [])),
    }


def typed_distinction_for(candidate: Dict[str, Any],
                          collision_hits: List[Dict[str, Any]]) -> str:
    """Assign the typed distinction class from the candidate's own
    recorded novelty surface (deterministic marker matching). A recorded
    cross-domain transition IS the retarget marker (deterministic from
    recorded state). When no distinction marker is present AND collisions
    exist, the honest class is NO_MEANINGFUL_DISTINCTION."""
    if candidate.get("cross_domain_transition"):
        return "NEW_APPLICATION"
    text = " ".join(str(candidate.get(k) or "") for k in
                    ("unexploited_phenomenon", "intervention", "problem",
                     "cross_domain_transition", "predicted_effect")).lower()
    for markers, cls in _DISTINCTION_RULES:
        if any(m in text for m in markers):
            return cls
    if collision_hits:
        return "NO_MEANINGFUL_DISTINCTION"
    # no collision and no marker: the default honest class for a
    # campaign-internal novel mechanism is NEW_MECHANISM, but the
    # prior-art stage must validate it (the attacker may demote).
    return "NEW_MECHANISM"


def _as_ms_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt an R411 candidate to the mechanism_space comparison shape,
    including the mechanism_graph (the causal core the distinctness
    instrument compares)."""
    from discovery_fabric.engine.mechanism_space import \
        build_mechanism_graph
    mech = " -> ".join(str(s) for s in (candidate.get("causal_chain") or []))
    intervention = str(candidate.get("intervention", ""))
    predicted = str(candidate.get("predicted_effect", ""))
    graph = build_mechanism_graph(
        {"fields": {"mechanism": {"value": mech}}},
        {"intervention": intervention,
         "mechanism": mech,
         "predicted_effect": predicted})
    return {
        "candidate_id": candidate.get("candidate_id"),
        "mechanism": mech or intervention,
        "intervention": intervention,
        "predicted_effect": predicted,
        "novel_design_variable": candidate.get("governing_variables", ""),
        "known_failure_modes": [f.get("failure_mode", "")
                                for f in candidate.get("failure_modes") or []],
        "constraint_set": {"boundary_conditions":
                           candidate.get("boundary_conditions", "")},
        "testable_prediction": (candidate.get("killer_experiment") or {}).get(
            "kill_condition", ""),
        "mechanism_graph": graph,
    }


def intra_campaign_dedup(
        candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Art. XLVIII: distinctness measured, not counted. Pairwise
    comparison via the repo instrument; EQUIVALENT candidates merge into
    one survivor (provenance of both preserved); INDETERMINATE pairs are
    recorded and referred to the prior-art stage; DISTINCT survive."""
    survivors: List[Dict[str, Any]] = []
    merges: List[Dict[str, Any]] = []
    indeterminate_pairs: List[Dict[str, Any]] = []
    for cand in candidates:
        ms_cand = _as_ms_candidate(cand)
        merged_into = None
        for i, surv in enumerate(survivors):
            comp = compare_candidates(ms_cand, _as_ms_candidate(surv))
            verdict = comp.get("verdict") or comp.get("relation")
            if verdict == "EQUIVALENT":
                merges.append({
                    "merged": cand["candidate_id"],
                    "into": surv["candidate_id"],
                    "basis": comp.get("basis") or comp.get("recorded_basis"),
                })
                surv.setdefault("merged_with", []).append(
                    cand["candidate_id"])
                surv.setdefault("evidence_refs", []).extend(
                    [r for r in cand.get("evidence_refs", [])
                     if r not in surv.get("evidence_refs", [])])
                merged_into = surv
                break
            if verdict == "INDETERMINATE":
                indeterminate_pairs.append({
                    "a": surv["candidate_id"],
                    "b": cand["candidate_id"],
                    "basis": comp.get("basis") or comp.get("recorded_basis"),
                })
        if merged_into is None:
            survivors.append(dict(cand))
    return {
        "collision_version": COLLISION_VERSION,
        "input_count": len(candidates),
        "survivor_count": len(survivors),
        "merge_events": merges,
        "indeterminate_pairs": indeterminate_pairs,
        "survivors": survivors,
    }


def collision_gate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Full s8 admission gate for ONE candidate: cemetery + portfolio +
    typed distinction. Returns {admitted, verdict, reasons...}."""
    cem = check_cemetery(candidate)
    if cem.get("status") != "OK":
        # Art. LXI: infrastructure failure is not scientific rejection —
        # the candidate is INCOMPLETE, never REJECTED
        return {
            "admitted": False,
            "verdict": "INCOMPLETE_CEMETERY_INFRASTRUCTURE",
            "cemetery": cem,
            "reasons": [cem.get("error", "cemetery infrastructure failure")],
        }
    hard_blocked = bool(cem.get("hard_blocks"))
    warned = cem.get("cemetery_verdict") == "WARNING"
    port_hits = _portfolio_overlap(candidate)
    collisions = []
    if hard_blocked or warned:
        collisions.append({"surface": "cemetery", "detail": cem})
    if port_hits:
        collisions.append({"surface": "portfolio", "detail": port_hits})
    typed = typed_distinction_for(candidate, collisions)
    if hard_blocked:
        # PROVEN_INVARIANT violation: physics proven impossible for this
        # class — the only unconditional rejection (the repo's own rule).
        return {
            "admitted": False,
            "verdict": "REJECTED_CEMETERY_PROVEN_INVARIANT",
            "cemetery": cem,
            "portfolio_hits": port_hits,
            "typed_distinction": typed,
            "reasons": ["PROVEN_INVARIANT hard-block from "
                        "MECHANISM_CEMETERY"],
        }
    if collisions and typed == "NO_MEANINGFUL_DISTINCTION":
        return {
            "admitted": False,
            "verdict": "REJECTED_NO_MEANINGFUL_DISTINCTION",
            "cemetery": cem,
            "portfolio_hits": port_hits,
            "typed_distinction": typed,
            "reasons": [
                "collision without a typed distinction "
                f"(cemetery_warning={warned}, "
                f"portfolio_hits={port_hits})"],
        }
    return {
        "admitted": True,
        "verdict": "ADMITTED_WITH_COLLISION_HISTORY" if collisions
        else "ADMITTED_NO_COLLISION",
        "cemetery": cem,
        "portfolio_hits": port_hits,
        "typed_distinction": typed,
        "reasons": [],
    }
