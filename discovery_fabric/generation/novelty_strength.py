#!/usr/bin/env python3
"""discovery_fabric/generation/novelty_strength.py — the R146 DIR-2
(TOP) + DIR-6 lever: NOVELTY STRENGTH at generation time.

The measured gap (V112, the auditor's sealed scoring): the strength
kit closed the off-target failure mode (0/30) but novelty is 4/30 =
13% strong vs the >=30% bar; the sealed mean is borderline (~3.1-3.3)
— the inventions are on-physics and quantified but OBVIOUS: they
propose the class the closest conventional practice would reach for
first, with routine parameter changes.

THE LEVER (two parts, both wired into the generation prompt BEFORE
the machine call — deterministic, zero LLM):

(1) THE EPO PROBLEM-SOLUTION CONDITIONING (DIR 2): the prompt forces
the problem-solution reasoning IN ORDER — name the CLOSEST
CONVENTIONAL PRACTICE for this failure class; state the
DISTINGUISHING FEATURES your mechanism has that it lacks; state the
OBJECTIVE TECHNICAL PROBLEM those features solve; ONLY THEN propose
the mechanism — with the explicit rejection clause: a routine
parameter change to the closest practice (bigger/thicker/more
frequent/harder) is NOT a distinguishing feature; the mechanism must
change HOW the failure physics is acted on, not how much.

(2) THE MOOSE-CHEM HYPOTHESIS RANKING (DIR 6): the allowed mechanism
classes are RANKED by transfer distance before the generator chooses
— the insight leveraged from MOOSE-Chem: non-obviousness comes from
CROSS-DOMAIN transfer, and the ranking makes the transfer distance a
first-class decision input instead of incidental prompt context. Each
mapped class carries a cross_domain precedent; the rank orders the
classes by (a) the precedent's domain distance from the problem's
domain (the typed DOMAIN_FAMILIES table), and (b) the conventional-
response demotion (the class the closest conventional practice uses
ranks LAST — it is the obvious candidate the EPO step rejects). The
prompt names the ranked order + the basis; the physics constraint
(the map's allowed classes) is UNCHANGED — the ranking reorders
PREFERENCE, never admits an off-target class.

Honesty: both parts are deterministic prompt conditioning; the
generator still owns the mechanism; the novelty_gate screen stays the
post-hoc input (never the verdict, Art. 14); nothing here invents a
number.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .mechanism_map import (FAILURE_CLASSES, MECHANISM_MAP,
                            OFF_TARGET_REJECTIONS, classify_failure)

# the domain-family table (typed, small): a precedent from a DISTANT
# family is a longer transfer (higher novelty-strength potential) than
# one from the problem's own family. Same family = 0, the listed
# adjacency = 1, everything else = 2.
DOMAIN_FAMILIES: Dict[str, List[str]] = {
    "aerospace": ["energy-turbines"],
    "energy-turbines": ["aerospace"],
    "marine": ["water-treatment", "offshore-energy"],
    "water-treatment": ["marine"],
    "mineral-processing": ["manufacturing", "rail"],
    "manufacturing": ["mineral-processing", "rail", "electronics"],
    "rail": ["mineral-processing", "manufacturing"],
    "biomedical": [],
    "electronics": ["manufacturing"],
    "civil": ["offshore-energy"],
    "offshore-energy": ["civil", "marine", "energy-turbines"],
    "automotive": ["aerospace", "rail"],
    "food-processing": ["water-treatment", "manufacturing"],
    "agriculture": ["food-processing"],
    "hvac": ["energy-turbines", "electronics"],
    "chemical-process": ["water-treatment", "manufacturing"],
}

# the conventional first response per failure class — the OBVIOUS
# candidate the EPO rejection clause names. Typed from the map's own
# physics; the mapped class closest to it is demoted to last in the
# ranking (it is what a skilled engineer reaches for first, which is
# exactly what non-obviousness is measured AGAINST).
CONVENTIONAL_FIRST_RESPONSE: Dict[str, str] = {
    "abrasion_erosion": ("a harder/thicker surface: apply a hard-facing "
                         "or add material at the wear site"),
    "fouling_deposition": ("clean more often: schedule more frequent "
                           "chemical/mechanical cleaning"),
    "nucleation_phase_change": ("add insulation or heat to keep the "
                                "material away from the phase boundary"),
    "residual_stress_distortion": ("add support/fixturing to resist the "
                                   "distortion after it is stressed"),
    "thermal_attack_surface": ("more cooling flow or more insulation "
                               "at the hot face"),
    "diffusion_intermetallic": ("a thicker barrier layer between the "
                                "mating materials"),
    "particle_attachment": ("periodic cleaning of the attached matter"),
    "granular_channeling": ("redistribute the flow by adding internal "
                            "baffles"),
    "thermal_fatigue_crack": (" thicker sections or more frequent "
                              "inspection at the crack site"),
    "mechanical_overload": ("a bigger/stronger member in the load path"),
    "deposition_fouling": ("clean more often: schedule more frequent "
                           "cleaning of the deposit"),
    "mechanical_clogging": ("clear the clog more often / enlarge the "
                            "passage"),
    "electrochemical_corrosion": ("a better coating or more inhibitor "
                                  "dosing"),
    "seal_leak_integrity": ("a tighter/better seal of the same type"),
    "phase_carryover_liquid": ("a bigger separator of the same type"),
    "corrosion_chemical": ("a better coating or more inhibitor dosing"),
    "contamination_separation": ("filter the contaminant more often / "
                                 "finer"),
    "fatigue_crack": ("grind out and inspect the crack site more "
                      "often / thicker sections at the stress "
                      "concentration"),
    "vibration_resonance": ("stiffen the structure or add damping "
                            "mass at the vibration site"),
    "thermal_mismatch": ("more compliant mounting or looser "
                         "tolerances at the joint"),
    "leakage_sealing": ("a tighter/better seal of the same type"),
    "electrical_insulation": ("more insulation material / higher "
                              "dielectric rating at the site"),
}


def _family_of(domain: str) -> Optional[str]:
    d = (domain or "").lower()
    for fam, keys in DOMAIN_FAMILIES.items():
        if any(k in d or d in k for k in [fam] + keys):
            if fam in d or d in fam:
                return fam
    return None


def transfer_distance(problem_domain: str, precedent_text: str) -> int:
    """0 = same family, 1 = adjacent, 2 = distant. The precedent text
    is the map's cross_domain field (e.g. 'helicopter rotor
    rain-erosion elastomer boots'); a precedent that names the
    problem's own family is the shortest transfer."""
    pf = _family_of(problem_domain)
    if pf is None:
        return 1  # untyped problem domain: neutral distance
    best = 2
    for fam, adj in DOMAIN_FAMILIES.items():
        # does the precedent text name this family?
        if any(k in precedent_text.lower() for k in [fam.replace('-', ' '),
                                                     fam.replace('-', '')]):
            if fam == pf:
                best = min(best, 0)
            elif fam in adj:
                best = min(best, 1)
            else:
                best = min(best, 2)
    return best


def rank_mechanism_hypotheses(problem_text: str,
                              problem_domain: str = "") -> Dict[str, Any]:
    """THE MOOSE-CHEM HYPOTHESIS RANKING (DIR 6): order the allowed
    mechanism classes for the detected failure class by transfer
    distance (descending — the longer cross-domain transfer carries
    the higher novelty-strength potential) with the conventional-
    response class demoted last. Returns the ranked list + the typed
    basis per class. Never admits a class outside the map (the
    off-target constraint is untouched)."""
    sel = classify_failure(problem_text)
    if sel.failure_class in ("", "unclassified"):
        return {"failure_class": "unclassified", "ranked": [],
                "note": "no failure class detected — no ranking (the "
                        "map's constraint block still rides the prompt)"}
    entries = MECHANISM_MAP.get(sel.failure_class, [])
    conv = CONVENTIONAL_FIRST_RESPONSE.get(sel.failure_class, "")
    ranked = []
    for e in entries:
        td = transfer_distance(problem_domain, e.get("cross_domain", ""))
        # the conventional-response demotion: a class whose 'why' is
        # materially the conventional move (add/apply more material at
        # the site, clean more often) ranks last
        w = e.get("why", "").lower()
        is_conv = any(s in w for s in (
            "harder surface", "thicker barrier", "more frequent",
            "bigger", "add material", "enlarge"))
        ranked.append({"mech_class": e["mech"], "why": e["why"],
                       "cross_domain": e.get("cross_domain", ""),
                       "transfer_distance": td,
                       "conventional_proximity": is_conv,
                       "rank_basis": (
                           f"transfer_distance={td} "
                           f"({'distant' if td == 2 else 'adjacent' if td == 1 else 'same-family'})"
                           + ("; demoted: materially the conventional "
                              "first response" if is_conv else ""))})
    # sort: transfer distance DESC, conventional proximity LAST
    ranked.sort(key=lambda r: (-r["transfer_distance"],
                               r["conventional_proximity"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return {"failure_class": sel.failure_class,
            "problem_domain": problem_domain,
            "conventional_first_response": conv,
            "ranked": ranked,
            "typed": ("MOOSE-Chem-style hypothesis ranking: the "
                      "cross-domain transfer distance orders the "
                      "allowed classes; the conventional-response "
                      "class is demoted (it is the obvious candidate "
                      "non-obviousness is measured against)")}


def epo_prompt_block(ranking: Dict[str, Any]) -> str:
    """THE EPO PROBLEM-SOLUTION CONDITIONING (DIR 2): forces the
    problem-solution reasoning order + the routine-change rejection
    clause. Rides the generation prompt alongside the map's constraint
    block."""
    if not ranking.get("ranked"):
        return ("NOVELTY-STRENGTH (typed): no failure class detected — "
                "state the failure physics explicitly and propose a "
                "mechanism that changes HOW the physics is acted on.")
    fc = ranking["failure_class"]
    conv = ranking.get("conventional_first_response", "")
    ranked = ranking["ranked"]
    lines = [
        "NOVELTY-STRENGTH CONDITIONING (the inventive-step shape, "
        "EPO problem-solution approach). Work through these steps IN "
        "ORDER and answer each explicitly in your NOVELTY STATEMENT:",
        f"1. CLOSEST CONVENTIONAL PRACTICE for this failure class "
        f"({fc}): "
        + (conv or "the practice a skilled engineer would "
                    "reach for first")
        + ".",
        "2. DISTINGUISHING FEATURES: what your mechanism HAS that the "
        "closest practice LACKS. A routine parameter change (bigger, "
        "thicker, harder, more frequent, higher dose) is NOT a "
        "distinguishing feature — name a change in HOW the failure "
        "physics is acted on (a different physical coupling), not how "
        "much of the same coupling.",
        "3. OBJECTIVE TECHNICAL PROBLEM: the technical problem those "
        "distinguishing features actually solve, phrased without the "
        "solution's words.",
        "4. MECHANISM: propose it — prefer the HIGHER-RANKED mechanism "
        "classes below (the longer cross-domain transfer carries the "
        "higher non-obviousness potential; the precedent named is real "
        "and checkable — transfer its physics, do not copy its domain "
        "blindly):",
    ]
    for r in ranked:
        star = "*" if r["rank"] == 1 else " "
        lines.append(
            f" {star} {r['rank']}. {r['mech_class']} "
            f"(transfer {r['transfer_distance']}; precedent: "
            f"{r['cross_domain'][:110]})")
    lines.append(
        "5. PREDICTION: ONE quantitative falsifiable prediction with "
        "units, computed from the problem's own numbers where given "
        "(a running calculation: name the formula, the inputs, the "
        "units, the result). Numbers NOT present in the problem and "
        "NOT computed from a named formula are FORBIDDEN — if a "
        "parameter is missing, state its assumed value and mark it "
        "'assumed'.")
    return "\n".join(lines)


def novelty_strength_block(problem_text: str,
                           problem_domain: str = "") -> Dict[str, Any]:
    """The one-call conditioning: the ranking (typed, rides the row)
    + the EPO prompt block (rides the prompt)."""
    ranking = rank_mechanism_hypotheses(problem_text, problem_domain)
    return {"ranking": ranking,
            "prompt_block": epo_prompt_block(ranking)}
