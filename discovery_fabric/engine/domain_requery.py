"""discovery_fabric/engine/domain_requery.py — the R145 DIR-4 lever:
the domain-anchored RE-QUERY on zero classification support.

The measured wind root cause (R144S1 close, typed): the retrieval
served arxiv GEOMETRY/MATHEMATICS papers ('Hilbert Geometry',
'Sasakian Geometry and Einstein Metrics', 'Noether's Theorem in
Multisymplectic Geometry') for 'wind blade leading-edge erosion' —
the primary query's device+failure terms keyed on the GEOMETRIC
senses of 'blade'/'leading edge'; the classifier correctly typed the
records 0 DIRECT/PARTIAL (5 ANALOGY + 7 IRRELEVANT) -> NO_EVIDENCE
-> 0 candidates -> the enrichment (which needs candidates) never
fires. The R143-F5 finding ('the synthesis complement did not
unstarve wind') is explained: the complement sits DOWNSTREAM of the
actual break.

THE LEVER (the R145 direction): when the classification returns ZERO
support, fire ONE typed second retrieval with the problem's DOMAIN
ANCHORS forced into the query — the failure-mechanism family
vocabulary (failure_mechanism_map.py, the R144 lever (a)) is the
anchor source — and a deterministic math-paper exclusion so pure
mathematics records cannot crowd the fresh set for an engineering
problem (the measured failure class).

Honesty boundaries (Art. XXV / Art. XLIII):
- ONE re-query, never more (a typed second pass, not a search loop);
- the anchor terms are DERIVED from the problem's own failure family
  + device terms (deterministic tables, no solution-class injection
  beyond the family's physics vocabulary, derivation class
  DOMAIN_ANCHOR_REQUERY);
- every fresh record rides the SAME classifier (no support is
  invented — a fresh record only counts when IT classifies
  DIRECT_SUPPORT/PARTIAL_SUPPORT);
- pure-math records are excluded with a typed reason
  (REQUERY_EXCLUDED_MATH) — never silently dropped;
- everything recorded: the query, the anchors, the excluded ids, the
  fresh classification counts, the promoted ids.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# the failure family -> domain anchor phrases (the family vocabulary
# the R144 map already types; the physics words a SAME-DOMAIN scholar
# search needs). Keys are failure_mechanism_map families.
DOMAIN_ANCHORS: Dict[str, List[str]] = {
    "abrasion_erosion": ["erosion", "wear", "coating protection",
                         "surface engineering"],
    "foreign_object": ["separation", "foreign object removal",
                       "debris exclusion"],
    "nucleation_phase_change": ["nucleation control", "freezing rate",
                                "crystallization"],
    "residual_stress_distortion": ["residual stress", "distortion",
                                   "stress relief"],
    "thermal_attack_surface": ["thermal protection", "cooling",
                               "heat flux"],
    "diffusion_intermetallic": ["diffusion barrier", "intermetallic",
                                "interface"],
    "particle_attachment": ["particle attachment", "froth",
                            "surface chemistry"],
    "granular_channeling": ["flow distribution", "granular flow",
                            "redistribution"],
    "thermal_fatigue_crack": ["thermal fatigue", "cyclic stress",
                              "expansion"],
    "mechanical_overload": ["load path", "reinforcement", "impact"],
}

# the pure-mathematics exclusion lexicon (the measured failure class:
# arxiv geometry/theory papers served for an engineering problem).
# Structural title vocabulary, closed classes only.
MATH_TITLE_RX = re.compile(
    r"\b(?:geometry|geometric|topolog\w+|manifold|theorem|lemma|"
    r"corollar\w+|algebra\w*|cohomolog\w+|homotop\w+|homolog\w+|"
    r"sphere packing|curvature|hypersurfac\w*|kahler|sasakian|"
    r"symplectic|riemannian|noether|isoperimetr\w+|variational "
    r"problem|einstein metrics|dilatation structures)\b", re.I)

# the engineering-problem guard: only fire the math exclusion when
# the problem's own text carries engineering vocabulary (an
# engineering problem excluding a math record is domain hygiene; a
# MATH problem excluding them would be absurd — and the map only
# detects engineering failure families anyway).
_ENGINEERING_RX = re.compile(
    r"\b(?:turbine|bearing|pump|heat exchanger|conveyor|reactor|"
    r"compressor|boiler|duct|blade|valve|motor|generator|cell|"
    r"line|mill|plant|machine|equipment|erosion|wear|fatigue|"
    r"corrosion|fouling)\b", re.I)


def anchored_query(problem: Dict[str, Any],
                   family: Optional[str]) -> Optional[Dict[str, Any]]:
    """The typed re-query view: a problem dict whose device +
    failure_mode fields carry the DOMAIN-ANCHORED form (the family's
    physics phrases + the problem's own device head terms), or None
    when no family is detected (no anchors -> no re-query, Art. XXV).
    """
    if family is None or family not in DOMAIN_ANCHORS:
        return None
    device = " ".join(str(problem.get("device") or "").split())
    # the device head terms: the text up to the first parenthetical
    # (spec clutter cut), first 6 content words — the device's own
    # domain identity, e.g. 'onshore wind turbine'
    head = " ".join(device.split("(")[0].split()[:6]).strip()
    anchors = " ".join(DOMAIN_ANCHORS[family])
    fm = " ".join(str(problem.get("failure_mode") or "")
                  .replace("_", " ").split())
    q = f"{head} {fm} {anchors}".strip()
    if not q:
        return None
    return {"device": head, "failure_mode": f"{fm} {anchors}".strip(),
            "problem_id": str(problem.get("problem_id") or ""),
            "requery_note": (
                "DOMAIN_ANCHOR_REQUERY (R145 DIR-4): the primary "
                f"retrieval returned zero support for the {family} "
                "failure family; this second query forces the "
                "family's domain anchor phrases alongside the "
                "problem's own device terms")}


def exclude_math(records: List[Dict[str, Any]],
                 problem: Dict[str, Any]) -> Tuple[List[Dict[str, Any]],
                                                   List[Dict[str, Any]]]:
    """(kept, excluded) split of fresh records: pure-math titles are
    excluded with a typed reason when the problem is an engineering
    problem (the measured failure class — arxiv math papers served
    for wind-blade erosion)."""
    if not _ENGINEERING_RX.search(
            " ".join(str(problem.get(k) or "") for k in
                     ("device", "failure", "failure_mode", "problem"))):
        return records, []
    kept, excluded = [], []
    for r in records or []:
        title = str(r.get("title") or "")
        if title and MATH_TITLE_RX.search(title):
            excluded.append({"id": r.get("id") or r.get("source"),
                             "title": title[:120],
                             "reason": "REQUERY_EXCLUDED_MATH"})
        else:
            kept.append(r)
    return kept, excluded


def zero_support_requery(env, problem: Dict[str, Any],
                         family: Optional[str]) -> Optional[Dict[str, Any]]:
    """The ONE typed second retrieval on zero support. Returns the
    re-query record (query + fresh records + fresh classification +
    promoted ids) or None (no family / no fresh records / transport
    total failure — every case typed, never an invented support).
    Caller: the mechanism-space stage, BEFORE the structured items
    are built (the fresh DIRECT/PARTIAL items ride the SAME joined
    build — nothing downstream knows a re-query happened except the
    tag)."""
    from .stage_entry import verified_evidence_items
    if verified_evidence_items(env):
        return None  # support exists — no re-query (the lever is 0-support only)
    view = anchored_query(problem, family)
    if view is None:
        return {"state": "NO_FAMILY", "family": family,
                "note": "no failure family detected — no anchors, "
                        "no re-query (Art. XXV)"}
    from discovery_fabric.retrieval_fabric.pipeline import (
        retrieve_fabric)
    try:
        fresh, report = retrieve_fabric(view)
    except Exception as e:  # noqa: BLE001 — typed degradation
        return {"state": "TRANSPORT_FAILED", "family": family,
                "query": view["failure_mode"],
                "error": f"{type(e).__name__}: {str(e)[:160]}"}
    fresh, excluded = exclude_math(fresh, problem)
    if not fresh:
        return {"state": "NO_FRESH_RECORDS", "family": family,
                "query": view["failure_mode"],
                "excluded_math": excluded,
                "note": "the re-query returned no non-math records "
                        "(typed, never an invented support)"}
    # the SAME classifier over the fresh records + the problem's
    # mechanism map (the env's map, verbatim — no second evaluator)
    mech_map = getattr(env, "mechanism_map", None) or {}
    from .evidence_classification import classify_evidence_set
    cls = classify_evidence_set(fresh, problem, mech_map)
    from .stage_entry import VERIFYING_CLASSES
    promoted = [it for it in (cls.get("items") or [])
                if it.get("classification") in VERIFYING_CLASSES]
    return {
        "state": "RUN", "family": family,
        "query": view["failure_mode"],
        "derivation_class": "DOMAIN_ANCHOR_REQUERY",
        "n_fresh_records": len(fresh),
        "excluded_math": excluded,
        "fresh_counts": cls.get("counts"),
        "n_promoted": len(promoted),
        "promoted_ids": [it.get("source_id") for it in promoted],
        "fresh_evidence": fresh,
        "fresh_classification": cls,
        "report": {"n_lanes": len(report.get("lane_states", [])
                                  if isinstance(report, dict) else []),
                   "record": str(report.get("record", ""))[:80]
                   if isinstance(report, dict) else ""},
    }
